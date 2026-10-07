"""uv environments and subprocess boundaries."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .components import Component, ensure_component, load_components, verify_component
from .files import digest, write_json

CORE = ("memory", "assessment", "onboarding")
PROFILES = {"core": CORE, "web": (*CORE, "web"), "all": (*CORE, "web", "collector")}


@dataclass
class Context:
    root: Path
    components_dir: Path
    workspace: Path

    @property
    def components(self) -> dict[str, Component]:
        return load_components(self.root / "manifests/components.lock.json")

    def checkout(self, name: str) -> Path:
        return verify_component(self.components[name], self.components_dir)


def execution_environment(*, no_keys: bool = False) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
    }
    if no_keys:
        env = {
            k: v
            for k, v in env.items()
            if not any(word in k.upper() for word in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))
        }
        env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    env.update(
        UV_NO_PROGRESS="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        PYTHONNOUSERSITE="1",
    )
    return env


def run(command: list[str], *, cwd: Path, log: Path | None = None, no_keys: bool = True) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=execution_environment(no_keys=no_keys),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        # Default demo only uses no-key subprocesses; live output is not persisted here.
        log.write_text(result.stdout + "\n" + result.stderr)
    if result.returncode:
        location = f"; inspect {log}" if log else "; check dependencies and configuration"
        raise ValueError(f"{Path(command[0]).name} failed (exit {result.returncode}){location}")
    return result.stdout


def component_command(
    ctx: Context,
    component: str,
    args: list[str],
    *,
    cwd: Path,
    log: Path | None = None,
    no_keys: bool = True,
) -> str:
    for dependency in {"onboarding": ("memory", "assessment"), "web": ("assessment",)}.get(
        component, ()
    ):
        ctx.checkout(dependency)
    project = ctx.checkout(component)
    if not (project / ".venv").is_dir():
        raise ValueError(f"Missing {component} environment; run vclogic bootstrap")
    return run(
        ["uv", "run", "--offline", "--no-sync", "--project", str(project), *args],
        cwd=cwd,
        log=log,
        no_keys=no_keys,
    )


def environment_stamp(ctx: Context, name: str) -> dict:
    # Each lock's editable siblings are bound independently by Git SHA.
    return {
        "python": "3.12.12",
        "lock_sha256": digest(ctx.checkout(name) / "uv.lock"),
        "components": {key: ctx.components[key].commit for key in CORE},
    }


def bootstrap(ctx: Context, profile: str = "core", *, offline: bool = False) -> dict:
    if shutil.which("uv") is None or shutil.which("git") is None:
        raise ValueError("Install uv and Git before bootstrap")
    selected = PROFILES[profile]
    for name in selected:
        print(f"Checking pinned {name}...", flush=True)
        ensure_component(ctx.components[name], ctx.components_dir, offline=offline)
    for name in selected:
        if name == "memory":
            continue  # Validator is installed by onboarding's existing uv lock.
        project = ctx.checkout(name)
        receipt = project / ".venv/vclogic-suite-environment.json"
        stamp = environment_stamp(ctx, name)
        if receipt.is_file() and json.loads(receipt.read_text()) == stamp:
            continue
        print(f"Installing locked {name} environment...", flush=True)
        command = ["uv", "sync", "--locked", "--no-dev", "--python", "3.12.12"]
        if offline:
            command.append("--offline")
        run(command, cwd=project, log=ctx.workspace / "setup-logs" / f"{name}.log")
        write_json(receipt, stamp)
    if "web" in selected:
        frontend = ctx.checkout("web") / "web/frontend"
        receipt = frontend / "node_modules/.vclogic-suite-build.json"
        stamp = {
            "package_lock_sha256": digest(frontend / "package-lock.json"),
            "commit": ctx.components["web"].commit,
        }
        if not (
            (frontend / "dist/index.html").is_file()
            and receipt.is_file()
            and json.loads(receipt.read_text()) == stamp
        ):
            if offline:
                raise ValueError(
                    "Web assets missing in offline mode; bootstrap --profile web online"
                )
            print("Building pinned web frontend with npm ci...", flush=True)
            run(
                ["npm", "ci", "--no-audit", "--no-fund"],
                cwd=frontend,
                log=ctx.workspace / "setup-logs/npm-ci.log",
            )
            run(
                ["npm", "run", "build"],
                cwd=frontend,
                log=ctx.workspace / "setup-logs/npm-build.log",
            )
            write_json(receipt, stamp)
    return {"profile": profile, "components": list(selected), "ready": True}
