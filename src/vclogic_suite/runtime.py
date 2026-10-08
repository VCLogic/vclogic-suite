"""uv environments and subprocess boundaries."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .components import Component, ensure_component, load_components, verify_component
from .files import digest, write_json

FULL_EXTRAS = {
    "collector": ["browser", "youtube", "av", "av-local"],
    "assessment": ["embeddings", "personalized"],
    "onboarding": ["embeddings"],
    "web": ["embeddings"],
}

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
        env.update(
            PYTHON_DOTENV_DISABLED="1",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            HF_HUB_DISABLE_TELEMETRY="1",
            LANGSMITH_TRACING="false",
            LANGSMITH_TRACING_V2="false",
            LANGCHAIN_TRACING="false",
            LANGCHAIN_TRACING_V2="false",
        )
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


def progress(items, label):
    """Report completed steps, not estimated bytes or installation time."""
    items = list(items)
    total = len(items)
    for index, item in enumerate(items):
        bar = "#" * index + "-" * (total - index)
        print(f"{label} [{bar}] {index}/{total}: {item}", file=sys.stderr, flush=True)
        yield item
    print(f"{label} [{'#' * total}] {total}/{total}: complete", file=sys.stderr, flush=True)


def require_core(ctx: Context) -> None:
    """Check setup receipts without fetching or installing anything."""
    try:
        for name in CORE:
            project = ctx.checkout(name)
            if name == "memory":
                continue
            receipt = project / ".venv/vclogic-suite-environment.json"
            if not receipt.is_file() or json.loads(receipt.read_text()) != environment_stamp(
                ctx, name
            ):
                raise ValueError(f"Missing or stale {name} environment")
    except (ValueError, OSError) as error:
        raise ValueError(f"Reviewer setup incomplete: {error}. Run uv run vclogic init") from error


def bootstrap(
    ctx: Context,
    profile: str = "core",
    *,
    offline: bool = False,
    embeddings: bool = False,
    full: bool = False,
) -> dict:
    if shutil.which("uv") is None or shutil.which("git") is None:
        raise ValueError("Install uv and Git before bootstrap")
    selected = PROFILES[profile]
    if "web" in selected and any(shutil.which(tool) is None for tool in ("node", "npm")):
        raise ValueError("Install Node.js and npm for the web frontend, or use init --profile core")
    for name in progress(selected, "Verify repositories"):
        ensure_component(ctx.components[name], ctx.components_dir, offline=offline)
    for name in progress((name for name in selected if name != "memory"), "Install dependencies"):
        # Memory validator is installed by onboarding's existing uv lock.
        project = ctx.checkout(name)
        receipt = project / ".venv/vclogic-suite-environment.json"
        stamp = environment_stamp(ctx, name)
        extra_receipt = project / ".venv/vclogic-suite-embeddings.json"
        needs_embeddings = (embeddings or full) and name in {"onboarding", "assessment", "web"}
        extras = FULL_EXTRAS.get(name, []) if full else (["embeddings"] if needs_embeddings else [])
        full_receipt = project / ".venv/vclogic-suite-full.json"
        full_stamp = (
            {
                "environment": stamp,
                "extras": extras,
                "pdf_lock": digest(ctx.root / "configs/memory-pdf.lock")
                if name == "onboarding"
                else None,
            }
            if full
            else None
        )
        if (
            receipt.is_file()
            and json.loads(receipt.read_text()) == stamp
            and (
                not full
                or (full_receipt.is_file() and json.loads(full_receipt.read_text()) == full_stamp)
            )
            and (
                not needs_embeddings
                or (extra_receipt.is_file() and json.loads(extra_receipt.read_text()) == stamp)
            )
        ):
            continue
        print(f"Installing locked {name} environment...", file=sys.stderr, flush=True)
        command = ["uv", "sync", "--locked", "--no-dev", "--python", "3.12.12"]
        for extra in extras:
            command.extend(["--extra", extra])
        if offline:
            command.append("--offline")
        run(command, cwd=project, log=ctx.workspace / "setup-logs" / f"{name}.log")
        # Invalidate receipts before auxiliary setup so interrupted upgrades are retried.
        full_receipt.unlink(missing_ok=True)
        if full and name == "onboarding":
            pdf_command = [
                "uv",
                "pip",
                "install",
                "--python",
                str(project / ".venv/bin/python"),
                "--require-hashes",
                "-r",
                str(ctx.root / "configs/memory-pdf.lock"),
            ]
            if offline:
                pdf_command.append("--offline")
            run(pdf_command, cwd=project, log=ctx.workspace / "setup-logs/memory-pdf.log")
        write_json(receipt, stamp)
        if full:
            write_json(full_receipt, full_stamp)
        if needs_embeddings:
            write_json(extra_receipt, stamp)
        else:
            extra_receipt.unlink(missing_ok=True)
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
            print("Building pinned web frontend with npm ci...", file=sys.stderr, flush=True)
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
    result = {"profile": profile, "components": list(selected), "ready": True}
    if full:
        # Chromium assets are pinned by the component's locked Playwright version.
        collector = ctx.checkout("collector")
        if not offline:
            print("Installing Chromium browser assets...", file=sys.stderr, flush=True)
            run(
                [
                    "uv",
                    "run",
                    "--offline",
                    "--no-sync",
                    "--project",
                    str(collector),
                    "playwright",
                    "install",
                    "chromium",
                ],
                cwd=collector,
                log=ctx.workspace / "setup-logs/browser-install.log",
            )
        print("Checking browser and host prerequisites...", file=sys.stderr, flush=True)
        browser_ok = True
        try:
            run(
                [
                    "uv",
                    "run",
                    "--offline",
                    "--no-sync",
                    "--project",
                    str(collector),
                    "python",
                    "-c",
                    "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); b.close(); p.stop()",
                ],
                cwd=collector,
                log=ctx.workspace / "setup-logs/browser-check.log",
            )
        except ValueError:
            browser_ok = False
        requirements = {
            "ffmpeg": "Install ffmpeg with your operating system package manager.",
            "node": "Install a Node.js version supported by the web component.",
            "npm": "Install npm with Node.js.",
            "codex": "Install and authenticate Codex CLI for memory generation.",
            "agent-reach": "Install Agent Reach for the collector's portfolio search route.",
            "mcporter": "Install and configure mcporter for Agent Reach's Exa backend.",
        }
        missing = {
            name: advice for name, advice in requirements.items() if shutil.which(name) is None
        }
        if not browser_ok:
            missing["chromium"] = (
                "Inspect workspace/setup-logs/browser-check.log; install missing browser system libraries, then rerun init."
            )
        result.update(
            full=True,
            installed_extras=FULL_EXTRAS,
            missing_prerequisites=missing,
            ready=not missing,
            authentication_and_models="Not verified: authenticate Codex and providers, accept gated model licenses; selected weights download on first use.",
        )
    return result
