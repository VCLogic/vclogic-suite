"""The VCLogic data bundle: install it, rebuild predictions from runs, run the proposal evaluation."""

from __future__ import annotations

import filecmp
import shutil
import subprocess
from pathlib import Path

from .runtime import Context, execution_environment, long_path

# The runtime part of the bundle; research/ and rationale_annotation/ are read in place.
RUNTIME = ("configs", "inputs", "evaluation", "proposal-evaluation")
SKIPPED = {"desktop.ini", ".DS_Store", "Thumbs.db"}


def pipeline(ctx: Context) -> Path:
    return ctx.workspace / "research/pipeline"


def install_data(ctx: Context, bundle: Path) -> dict:
    """Copy the bundle's runtime folders into the research workspace, never overwriting."""
    bundle = bundle.resolve()
    if not (bundle / "configs/investors").is_dir() or not (bundle / "inputs/investors").is_dir():
        raise ValueError(
            f"Not a VCLogic data bundle (no configs/investors and inputs/investors): {bundle}"
        )
    target = long_path(pipeline(ctx))
    source = long_path(bundle)
    copies, present, conflicts = [], 0, []
    for folder in RUNTIME:
        if not (source / folder).is_dir():
            continue
        for path in sorted((source / folder).rglob("*")):
            if not path.is_file() or path.name in SKIPPED:
                continue
            relative = path.relative_to(source)
            destination = target / relative
            if not destination.exists():
                copies.append((path, destination))
            elif filecmp.cmp(path, destination, shallow=False):
                present += 1
            else:
                conflicts.append(relative.as_posix())
    if conflicts:
        shown = "\n  ".join(conflicts[:10])
        raise ValueError(
            f"{len(conflicts)} bundle files differ from files already in {pipeline(ctx)}; "
            f"nothing was copied. Move them aside or use a new --workspace:\n  {shown}"
        )
    for path, destination in copies:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    taxonomy = target / "inputs/taxonomy"
    added_taxonomy = False
    if not (taxonomy / "codebook_v_final.json").is_file():
        # The bundle omits the public taxonomy; the assessment repository ships it.
        shutil.copytree(ctx.checkout("assessment") / "inputs/taxonomy", taxonomy, dirs_exist_ok=True)
        added_taxonomy = True
    investors = sorted(p.parent.name for p in (target / "configs/investors").glob("*/rehearsal.toml"))
    return {
        "workspace": str(pipeline(ctx)),
        "copied_files": len(copies),
        "already_present": present,
        "taxonomy_added": added_taxonomy,
        "investors": investors,
        "next": "uv run vclogic web",
    }


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
        raise ValueError(f"No evaluation data in {data}; run uv run vclogic install-data PATH first")
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
