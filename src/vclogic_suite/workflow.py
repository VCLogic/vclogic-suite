"""Stage adapters using native CLIs and their existing artifact formats."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

from .files import safe_path
from .research import check_credentials
from .runtime import Context, component_command, execution_environment

STAGES = ("discover", "collect", "process", "memory", "onboard", "pipeline")
OPTIONS = {
    "discover": set(),
    "collect": set(),
    "process": {
        "--candidate-id",
        "--transcription-model",
        "--diarization-model",
        "--transcription-cost-usd",
        "--diarization-cost-usd",
    },
    "memory": {
        "--model",
        "--timeout",
        "--workers",
        "--reviews",
        "--identity-resolutions",
        "--supplements",
    },
    "onboard": {
        "--display-name",
        "--firm",
        "--role",
        "--alias",
        "--from-pitch-show",
        "--pitch-show-slug",
        "--pitch-show-cache",
        "--max-episodes",
        "--collect-only",
        "--decision-model",
        "--review",
    },
    "pipeline": set(),
}


def add_commands(commands):
    descriptions = {
        "discover": "Discover public traces with the collector's guided identity/source review",
        "collect": "Download selected sources using the collector's guided workflow",
        "process": "Process downloaded sources, export and verify the corpus",
        "memory": "Build and validate investment memory from the full collector export",
        "onboard": "Prepare, validate and install the investor bundle",
        "pipeline": "Run native historical assessment preflight, run and verify",
    }
    for name, description in descriptions.items():
        command = commands.add_parser(name, help=description, description=description)
        command.add_argument(
            "--investor", required=name != "discover", help="Collector investor slug"
        )
        if name == "discover":
            command.add_argument("--name", help="Investor name for a new discovery")
        if name in ("memory", "onboard", "pipeline"):
            command.add_argument(
                "--allow-paid", action="store_true", help="Permit model-backed generation"
            )
        if name == "onboard":
            command.add_argument(
                "--skip-indexes", action="store_true", help="Create a partial, non-ready bundle"
            )
        if name == "pipeline":
            command.add_argument(
                "--config", type=Path, help="Native canonical TOML inside the pipeline workspace"
            )
        command.add_argument(
            "native_args",
            nargs="...",
            help="Additional native options after -- (use absolute file paths)",
        )


def invoke(ctx: Context, component: str, command: list[str], *, cwd: Path) -> int:
    """Keep native prompts/progress interactive; do not persist credential-bearing logs."""
    for dependency in {"onboarding": ("memory", "assessment")}.get(component, ()):
        ctx.checkout(dependency)
    project = ctx.checkout(component)
    if not (project / ".venv").is_dir():
        raise ValueError(f"Missing {component} environment; run uv run vclogic init")
    return subprocess.call(
        ["uv", "run", "--offline", "--no-sync", "--project", str(project), *command],
        cwd=cwd,
        env=execution_environment(no_keys=False),
    )


def run_stage(ctx: Context, args) -> int:
    slug = args.investor
    if slug is not None and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Invalid investor slug; use the slug reported by discovery")
    extras = list(args.native_args)
    if extras[:1] == ["--"]:
        extras.pop(0)
    for token in extras:
        if token.startswith("-") and not re.fullmatch(r"-\d+(\.\d+)?", token):
            if token.split("=", 1)[0] not in OPTIONS[args.command]:
                raise ValueError(
                    f"Unsupported native option {token.split('=', 1)[0]}; suite manages paths and stage selection"
                )
    root = ctx.workspace / "research"
    traces = root / "traces"
    pipeline = root / "pipeline"
    wiki = root / "wiki" / (slug or "")
    bundle = root / "bundles" / (slug or "")
    if args.command in ("memory", "pipeline") and not args.allow_paid:
        raise ValueError("This stage requires --allow-paid for configured model generation")
    if (
        args.command == "onboard"
        and "--from-pitch-show" in extras
        and "--collect-only" not in extras
        and not args.allow_paid
    ):
        raise ValueError("Pitch Show extraction requires --allow-paid (or --collect-only)")
    root.mkdir(parents=True, exist_ok=True)
    calls = []
    if args.command in ("discover", "collect"):
        command = [
            "vc-trace-collector",
            "wizard",
            "--stage",
            "discover" if args.command == "discover" else "download",
            "--output-dir",
            str(traces),
        ]
        if slug:
            command += ["--investor", slug]
        if args.command == "discover" and args.name:
            command += ["--name", args.name]
        calls.append(("collector", command))
    elif args.command == "process":
        for operation in ("process", "export", "verify"):
            command = [
                "vc-trace-collector",
                operation,
                "--investor",
                slug,
                "--output-dir",
                str(traces),
            ]
            calls.append(("collector", command + (extras if operation == "process" else [])))
    elif args.command == "memory":
        if shutil.which("codex") is None:
            raise ValueError(
                "Memory full-build requires authenticated Codex CLI on PATH; .env API keys do not replace Codex authentication"
            )
        if wiki.exists():
            raise ValueError(
                f"Memory output already exists: {wiki}; preserve it or choose a new --workspace"
            )
        # Verify source export before paid generation; do not rewrite legacy admission rules.
        calls.append(
            (
                "collector",
                ["vc-trace-collector", "verify", "--investor", slug, "--output-dir", str(traces)],
            )
        )
        calls.append(
            (
                "onboarding",
                [
                    "investor-memory",
                    "full-build",
                    str(traces / slug),
                    "--output",
                    str(wiki),
                    "--cache-dir",
                    str(root / "memory-cache" / slug),
                    *extras,
                ],
            )
        )
        calls.append(("onboarding", ["investor-memory", "check", str(wiki)]))
    elif args.command == "onboard":
        command = [
            "investor-onboarding",
            "prepare",
            "--wiki",
            str(wiki),
            "--output",
            str(bundle),
            *extras,
        ]
        if args.skip_indexes:
            command.append("--skip-indexes")
        calls.append(("onboarding", command))
    elif args.command == "pipeline":
        config_path = args.config or Path(f"configs/investors/{slug}/canonical.toml")
        if config_path.is_absolute():
            try:
                config_path = config_path.relative_to(pipeline)
            except ValueError as error:
                raise ValueError("Config must be inside the pipeline workspace") from error
        config_path = safe_path(pipeline, config_path.as_posix())
        config = tomllib.loads(config_path.read_text())
        if config.get("run", {}).get("vc_slug") != slug:
            raise ValueError("Config investor does not match --investor")
        check_credentials(config)
        for operation in ("preflight", "run", "verify"):
            calls.append(
                ("assessment", ["vc-clone-graph", operation, "--config", str(config_path)])
            )
    for component, command in calls:
        print(f"{args.command}: {component} / {command[1]}", flush=True)
        code = invoke(ctx, component, command, cwd=pipeline if args.command == "pipeline" else root)
        if code:
            return code
    if args.command == "onboard":
        result = json.loads(
            component_command(
                ctx,
                "onboarding",
                ["investor-onboarding", "check", "--bundle", str(bundle)],
                cwd=root,
                no_keys=False,
            )
        )
        if result.get("valid") is not True:
            raise ValueError("Onboarding bundle validation failed")
        if not args.skip_indexes and result.get("ready_for_assessment") is not True:
            raise ValueError(
                "Bundle is not assessment-ready; inspect native validation before installing"
            )
        pipeline.mkdir(parents=True, exist_ok=True)
        code = invoke(
            ctx,
            "onboarding",
            [
                "investor-onboarding",
                "install",
                "--bundle",
                str(bundle),
                "--pipeline-workspace",
                str(pipeline),
            ],
            cwd=root,
        )
        if code:
            return code
        print(
            json.dumps(
                {
                    "workspace": str(pipeline),
                    "ready_for_assessment": result.get("ready_for_assessment", False),
                },
                indent=2,
            )
        )
    print(f"Stage finished. Research workspace: {root}", flush=True)
    return 0
