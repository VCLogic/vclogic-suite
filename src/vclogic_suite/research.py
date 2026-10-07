"""Explicit live adapters: delegate assessment and web behavior to component CLIs."""

from __future__ import annotations

import json
import os
import subprocess
import tomllib
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
                f"Missing required credential: {key}; export it explicitly before live execution"
            )


def launch(ctx: Context, args) -> int:
    if not args.allow_paid:
        raise ValueError(
            "Live research operations require --allow-paid; default demo requires no key"
        )
    workspace = args.research_workspace.resolve()
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
        command = [
            "vc-clone-web",
            "--pipeline-workspace",
            str(workspace),
            "--config",
            relative,
            "--static-root",
            str(static),
            "--port",
            str(args.port),
        ]
    else:
        command = [
            "vc-clone-rehearsal",
            "start",
            "--config",
            relative,
            "--vc",
            args.investor,
            "--pitch",
            str(args.pitch.resolve()),
            "--build-canonical-baseline",
        ]
        for company in args.company:
            command.extend(["--company", company])
    print(
        "Live operation enabled. Configured generation may incur cost; local models must be prepared.",
        flush=True,
    )
    return subprocess.call(
        ["uv", "run", "--offline", "--no-sync", "--project", str(project), *command],
        cwd=workspace,
        env=execution_environment(no_keys=False),
    )
