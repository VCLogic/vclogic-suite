"""Rebuild predictions.csv from assessment runs and run the proposal evaluation."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .runtime import Context, execution_environment


def pipeline(ctx: Context) -> Path:
    return ctx.workspace / "research/pipeline"


def _script(ctx: Context, name: str) -> Path:
    script = ctx.checkout("assessment") / "proposal-evaluation" / name
    if not script.is_file():
        raise ValueError(f"Assessment checkout lacks proposal-evaluation/{name}; run uv run vclogic init")
    return script


def build_predictions(ctx: Context, runs: list[Path], out: Path | None, force: bool) -> int:
    work = pipeline(ctx)
    work.mkdir(parents=True, exist_ok=True)
    out = (out or work / "proposal-evaluation/data/predictions.csv").resolve()
    if out.exists() and not force:
        raise ValueError(f"{out} exists; pass --out for a new file or --force to replace it")
    taxonomy = work / "proposal-evaluation/data/taxonomy.json"
    if not taxonomy.is_file():
        taxonomy = ctx.checkout("assessment") / "inputs/taxonomy/codebook_v_final.json"
    command = ["python", str(_script(ctx, "build_predictions.py")), "--out", str(out),
               "--taxonomy", str(taxonomy)]
    for folder in runs:
        command += ["--runs", str(folder.resolve())]
    return _run(ctx, command, cwd=work)


def evaluate(ctx: Context, *, quick: bool, annotations: Path | None, predictions: Path | None) -> int:
    work = pipeline(ctx)
    data = work / "proposal-evaluation/data"
    if not data.is_dir():
        raise ValueError(f"No evaluation inputs in {data}; put annotations.csv, predictions.csv and the other inputs there")
    command = ["python", str(_script(ctx, "evaluate.py")), "--data", str(data),
               "--out", str(work / "proposal-evaluation/results")]
    if quick:
        command.append("--quick")
    if annotations:
        command += ["--annotations", str(annotations.resolve())]
    if predictions:
        command += ["--predictions", str(predictions.resolve())]
    # Figures need matplotlib, which the assessment environment does not install.
    return _run(ctx, command, cwd=work, extra=["--with", "matplotlib>=3.8,<4"])


def _run(ctx: Context, command: list[str], *, cwd: Path, extra: list[str] | None = None) -> int:
    project = ctx.checkout("assessment")
    if not (project / ".venv").is_dir():
        raise ValueError("Missing assessment environment; run uv run vclogic init")
    offline = [] if extra else ["--offline"]
    return subprocess.call(
        ["uv", "run", *offline, "--no-sync", "--project", str(project), *(extra or []), *command],
        cwd=cwd,
        env=execution_environment(no_keys=True),
    )
