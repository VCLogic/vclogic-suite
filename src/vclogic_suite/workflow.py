"""Stage adapters using native CLIs and their existing artifact formats."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

from .files import safe_path
from .research import check_credentials
from .runtime import Context, component_command, execution_environment

STAGES = ("collect", "process", "memory", "onboard", "pipeline", "run")
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
OPTIONS = {
    "collect": set(),
    "process": {
        "--candidate-id",
        "--transcription-model",
        "--diarization-model",
        "--transcription-cost-usd",
        "--diarization-cost-usd",
    },
    "memory": {
        "--harness",
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
    "run": set(),
}


def settings(root: Path) -> dict:
    """Shared non-secret suite settings; a missing vclogic.toml means defaults."""
    path = root / "vclogic.toml"
    data = tomllib.loads(path.read_text()) if path.is_file() else {}
    if not isinstance(data.get("allow_paid", False), bool):
        raise ValueError("vclogic.toml: allow_paid must be true or false")
    for stage in ("process", "memory", "onboard"):
        extra = data.get(stage, {}).get("args", [])
        if not isinstance(extra, list) or not all(isinstance(item, str) for item in extra):
            raise ValueError(f"vclogic.toml: [{stage}] args must be a list of strings")
    return data


def allow_paid(ctx: Context, args) -> bool:
    return bool(getattr(args, "allow_paid", False) or settings(ctx.root).get("allow_paid"))


def add_commands(commands):
    descriptions = {
        "collect": "Guided collection: identity, sources, triage, download, process, export",
        "process": "Re-run processing, export and verification of downloaded sources",
        "memory": "Build and validate investment memory from the full collector export",
        "onboard": "Prepare, validate and install the investor bundle",
        "pipeline": "Run native historical assessment preflight, run and verify",
        "run": "New investor end to end: collect, memory, onboard, install for web/assess",
    }
    for name, description in descriptions.items():
        command = commands.add_parser(name, help=description, description=description)
        command.add_argument("--investor", help="Collector investor slug")
        if name in ("collect", "run"):
            command.add_argument("--name", help="Investor name for a new collection")
        if name in ("memory", "onboard", "pipeline", "run"):
            command.add_argument(
                "--allow-paid",
                action="store_true",
                help="Accept that this may spend money on model calls (memory, Pitch Show extraction)",
            )
        if name in ("onboard", "run"):
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


def proxy_warnings() -> list[str]:
    """The collector and mcporter ignore HTTP(S)_PROXY unless opted in; direct fetches then time out."""
    if not any(
        os.environ.get(name) for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")
    ):
        return []
    return [
        f"warning: a proxy is configured but {name}=1 is not set in .env; {effect}"
        for name, effect in (
            ("VC_TRACE_ALLOW_ENV_PROXY", "collector page fetches will bypass it and may time out"),
            ("NODE_USE_ENV_PROXY", "Agent Reach/Exa search through mcporter may appear offline"),
        )
        if os.environ.get(name) != "1"
    ]


def run_stage(ctx: Context, args) -> int:
    if args.command in ("collect", "process", "run"):
        for warning in proxy_warnings():
            print(warning, flush=True)
    slug = args.investor
    if slug is not None and not re.fullmatch(SLUG, slug):
        raise ValueError("Invalid investor slug; use the slug reported by collection")
    if args.command == "run":
        return run_all(ctx, args)
    if slug is None and args.command != "collect":
        raise ValueError(f"{args.command} requires --investor")
    if args.command == "collect" and not (slug or args.name):
        raise ValueError("collect requires --name for a new investor or --investor to resume")
    config = settings(ctx.root)
    extras = list(args.native_args)
    if extras[:1] == ["--"]:
        extras.pop(0)
    extras = [*config.get(args.command, {}).get("args", []), *extras]
    if args.command == "memory" and "--harness" not in {e.split("=", 1)[0] for e in extras}:
        extras = ["--harness", config.get("memory", {}).get("harness", "auto"), *extras]
    paid = allow_paid(ctx, args)
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
    if args.command in ("memory", "pipeline") and not paid:
        raise ValueError(
            "This stage requires --allow-paid (or allow_paid = true in vclogic.toml) for model generation"
        )
    if (
        args.command == "onboard"
        and "--from-pitch-show" in extras
        and "--collect-only" not in extras
        and not paid
    ):
        raise ValueError("Pitch Show extraction requires --allow-paid (or --collect-only)")
    root.mkdir(parents=True, exist_ok=True)
    calls = []
    if args.command == "collect":
        command = ["vc-trace-collector", "wizard", "--output-dir", str(traces)]
        command += ["--investor", slug] if slug else ["--name", args.name]
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
        if shutil.which("codex") is None and shutil.which("claude") is None:
            raise ValueError(
                "Memory full-build needs an authenticated Codex or Claude Code CLI on PATH; .env API keys do not replace their login"
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


def collected(traces: Path, slug: str) -> bool:
    state = traces / slug / "guided_state.json"
    return state.is_file() and "finish" in json.loads(state.read_text()).get("completed", [])


def run_all(ctx: Context, args) -> int:
    """Chain the stages for one investor; finished stages are skipped, so rerunning resumes."""
    if not (args.investor or args.name):
        raise ValueError("run requires --name for a new investor or --investor to resume")
    if not allow_paid(ctx, args):
        raise ValueError(
            "run includes memory generation; pass --allow-paid or set allow_paid = true in vclogic.toml"
        )
    if [arg for arg in args.native_args if arg != "--"]:
        raise ValueError(
            "run reads native options from vclogic.toml; use single stages for -- options"
        )
    root = ctx.workspace / "research"
    traces = root / "traces"
    slug = args.investor

    def stage(stage_name: str, **overrides) -> int:
        values = dict(
            command=stage_name,
            investor=slug,
            name=None,
            allow_paid=True,
            skip_indexes=args.skip_indexes,
            config=None,
            native_args=[],
        )
        values.update(overrides)
        return run_stage(ctx, argparse.Namespace(**values))

    if slug is None or not collected(traces, slug):
        before = set(traces.iterdir()) if traces.is_dir() else set()
        code = stage("collect", name=None if slug else args.name)
        if code:
            return code
        if slug is None:
            new = [
                path.name
                for path in (traces.iterdir() if traces.is_dir() else [])
                if path.is_dir() and path not in before
            ]
            # The collector reuses slugify(name) for an existing workspace and may add the firm for a new one.
            slug = (
                new[0]
                if len(new) == 1
                else re.sub(r"[^a-z0-9]+", "-", args.name.casefold()).strip("-")
            )
        if not re.fullmatch(SLUG, slug) or not collected(traces, slug):
            print(
                f"Collection is not finished. Resume with: uv run vclogic run --investor {slug}",
                flush=True,
            )
            return 1
    print(f"run: collection complete for {slug}", flush=True)
    wiki = root / "wiki" / slug
    if wiki.exists():
        print(f"run: memory exists, checking {wiki}", flush=True)
        code = invoke(ctx, "onboarding", ["investor-memory", "check", str(wiki)], cwd=root)
        if code:
            print("Existing memory is invalid; inspect it or use a new --workspace.", flush=True)
            return code
    else:
        code = stage("memory")
        if code:
            return code
    if (root / "pipeline/inputs/investors" / f"{slug}.toml").is_file():
        print("run: investor already installed in the pipeline workspace", flush=True)
    else:
        code = stage("onboard")
        if code:
            return code
    print(
        f"Investor {slug} is ready.\n"
        f"  Assess a pitch: uv run vclogic assess --investor {slug} --pitch /path/pitch.txt --company NAME\n"
        "  Web interface:  uv run vclogic web",
        flush=True,
    )
    return 0
