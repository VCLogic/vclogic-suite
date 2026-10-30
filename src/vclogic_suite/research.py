"""Explicit live adapters: delegate assessment and web behavior to component CLIs."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from .files import safe_path
from .runtime import Context, component_command, execution_environment


def check_credentials(config: dict) -> None:
    provider = config.get("provider", {})
    kind = provider.get("kind")
    if kind == "fake":
        raise ValueError("The fake provider is a fixed fixture; use vclogic demo instead")
    if kind not in ("openrouter", "openai", "ollama"):
        raise ValueError("Unsupported or missing research provider")
    if kind in ("openrouter", "openai"):
        key = (
            "OPENAI_API_KEY"
            if kind == "openai"
            else provider.get("api_key_env", "OPENROUTER_API_KEY")
        )
        if not os.environ.get(key):
            raise ValueError(
                f"Missing required credential: {key}; set it in the suite root .env or export it before live execution"
            )


def launch(ctx: Context, args) -> int:
    from .workflow import settings

    workspace = (args.research_workspace or ctx.workspace / "research/pipeline").resolve()
    if args.config is None and args.command == "web" and not args.investor:
        # Any installed rehearsal config starts the app; the UI then lists every installed investor.
        installed = sorted(workspace.glob("configs/investors/*/rehearsal.toml"))
        if not installed:
            raise ValueError("No installed investor; run uv run vclogic run --name NAME first")
        args.config = installed[0].relative_to(workspace)
    if args.config is None:
        if not args.investor or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.investor):
            raise ValueError(
                "Supply --investor for the installed rehearsal config or --config explicitly"
            )
        args.config = Path(f"configs/investors/{args.investor}/rehearsal.toml")
    if not workspace.is_dir():
        raise ValueError("Research workspace does not exist")
    # Native configs must belong to the selected workspace; never accept ../ escapes.
    if args.config.is_absolute():
        try:
            relative = args.config.resolve().relative_to(workspace).as_posix()
        except ValueError as error:
            raise ValueError("Config must be inside the research workspace") from error
    else:
        relative = args.config.as_posix()
    config_path = safe_path(workspace, relative)
    config = tomllib.loads(config_path.read_text())
    check_credentials(config)
    canonical = config.get("classification", {}).get("canonical_config_path")
    if not canonical:
        raise ValueError("Rehearsal config must specify classification.canonical_config_path")
    check_credentials(tomllib.loads(safe_path(workspace, canonical).read_text()))
    component = "web" if args.command == "web" else "assessment"
    ctx.checkout(component)
    if args.command == "assess" and not args.pitch.is_file():
        raise ValueError("Pitch file does not exist")
    probe = Path(__file__).with_name("research_probe.py")
    probe_args = ["python", str(probe), str(workspace), relative, args.command]
    if args.command == "assess":
        probe_args.append(args.investor)
    result = json.loads(component_command(ctx, component, probe_args, cwd=workspace))
    if not result.get("ready"):
        raise ValueError("Research assets not ready: " + "; ".join(result.get("errors", [])))
    project = ctx.checkout(component)
    if args.command == "web":
        static = project / "web/frontend/dist"
        if not (static / "index.html").is_file():
            raise ValueError("Web frontend missing; run bootstrap --profile web")
        port = args.port or settings(ctx.root).get("web", {}).get("port", 8000)
        command = [
            "vc-clone-web",
            "--pipeline-workspace",
            str(workspace),
            "--config",
            relative,
            "--static-root",
            str(static),
            "--port",
            str(port),
        ]
        for flag, folder in (("--investor-bundles", "bundles"), ("--investment-memory", "wiki")):
            if (ctx.workspace / "research" / folder).is_dir():
                command += [flag, str(ctx.workspace / "research" / folder)]
    else:
        session = f"{args.investor}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        command = [
            "vc-clone-rehearsal",
            "start",
            "--config",
            relative,
            "--vc",
            args.investor,
            "--pitch",
            str(args.pitch.resolve()),
            "--session",
            session,
            "--build-canonical-baseline",
        ]
        for company in args.company:
            command.extend(["--company", company])
    print(
        "Live operation enabled. Configured generation may incur cost; local models must be prepared.",
        flush=True,
    )
    code = subprocess.call(
        ["uv", "run", "--offline", "--no-sync", "--project", str(project), *command],
        cwd=workspace,
        env=execution_environment(no_keys=False),
    )
    if code or args.command == "web":
        return code
    # Read back the frozen Phase 1/Phase 2 assessment; this makes no model calls.
    output = ctx.workspace / "research/assessments" / args.investor
    output.mkdir(parents=True, exist_ok=True)
    for kind, suffix in (("json", "json"), ("markdown", "md")):
        text = component_command(
            ctx,
            "assessment",
            [
                "vc-clone-rehearsal",
                "assessment",
                "--config",
                relative,
                "--session",
                session,
                "--format",
                kind,
            ],
            cwd=workspace,
            no_keys=False,
        )
        (output / f"{session}.{suffix}").write_text(text)
    print(text, flush=True)
    print(f"Assessment saved: {output / session}.json and .md (session {session})", flush=True)
    return 0
