"""A truthful, no-key demonstration using existing component entry points."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from .files import copy_verified, digest, inventory, write_json
from .runtime import Context, bootstrap, component_command, require_core


def demo(ctx: Context, *, offline: bool = False, setup: bool = True) -> dict:
    if setup:
        bootstrap(ctx, offline=offline)
    else:
        require_core(ctx)
    artifacts = json.loads((ctx.root / "manifests/reviewer-artifacts.json").read_text())
    expectations_path = ctx.root / "expected_outputs/reviewer-demo/contract.json"
    expectations = json.loads(expectations_path.read_text())
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    directory = ctx.workspace / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    started = monotonic()
    report = {
        "schema_version": "vclogic-suite-demo-v1",
        "expectations_sha256": digest(expectations_path),
        "run_id": run_id,
        "run_directory": str(directory),
        "created_at": datetime.now(UTC).isoformat(),
        "investor": artifacts["investor"],
        "episode": artifacts["episode"],
        "paid_inference": False,
        "validation_passed": False,
        "publication": artifacts["publication"],
        "stages": {},
        "components": {name: row.commit for name, row in ctx.components.items()},
        "components_manifest_sha256": digest(ctx.root / "manifests/components.lock.json"),
        "artifacts_manifest_sha256": digest(ctx.root / "manifests/reviewer-artifacts.json"),
    }
    stage = "memory"
    try:
        print("Validating frozen Elizabeth Yin memory (no generation)...", flush=True)
        copy_verified(
            ctx.checkout("memory"), directory / "frozen-memory", artifacts["memory"]["files"]
        )
        wiki = directory / "frozen-memory" / artifacts["memory"]["path"]
        result = component_command(
            ctx,
            "onboarding",
            ["investor-memory", "check", str(wiki)],
            cwd=directory,
            log=directory / "logs/memory-check.log",
        )
        if json.loads(result).get("valid") is not True:
            raise ValueError("Memory validator did not report valid=true")
        report["stages"]["memory"] = {
            "mode": "frozen",
            "validation": "passed",
            "path": wiki.relative_to(directory).as_posix(),
        }
        stage = "onboarding"
        print(
            "Packaging and installing wiki-only onboarding bundle (indexes skipped)...", flush=True
        )
        bundle = directory / "onboarding-bundle"
        installed = directory / "onboarding-workspace"
        installed.mkdir()
        operations = [
            (
                "prepare",
                ["prepare", "--wiki", str(wiki), "--output", str(bundle), "--skip-indexes"],
            ),
            ("check", ["check", "--bundle", str(bundle)]),
            (
                "install",
                ["install", "--bundle", str(bundle), "--pipeline-workspace", str(installed)],
            ),
        ]
        check = None
        for name, args in operations:
            output = component_command(
                ctx,
                "onboarding",
                ["investor-onboarding", *args],
                cwd=directory,
                log=directory / f"logs/onboarding-{name}.log",
            )
            if name == "check":
                check = json.loads(output)
        if (
            not check
            or check.get("valid") is not True
            or check.get("ready_for_assessment") is not False
        ):
            raise ValueError("Unexpected wiki-only bundle validity/readiness")
        report["stages"]["onboarding"] = {
            "mode": "recomputed",
            "validation": "passed",
            "ready_for_assessment": False,
            "capabilities": check["capabilities"],
            "reason": "Semantic indexes deliberately not built; this is a valid partial bundle.",
        }
        stage = "assessment"
        print(
            "Running separate original Thoras assessment fixture (fake provider, v1)...", flush=True
        )
        workspace = directory / "assessment-workspace"
        copy_verified(ctx.checkout("assessment"), workspace, artifacts["assessment"]["files"])
        config = artifacts["assessment"]["config"]
        for action in ("index", "run", "verify"):
            component_command(
                ctx,
                "assessment",
                ["vc-clone-graph", action, "--config", config],
                cwd=workspace,
                log=directory / f"logs/assessment-{action}.log",
            )
        output = workspace / "outputs/fake-elizabeth-thoras" / artifacts["episode"]
        report["outputs"] = {
            name: (output / relative).relative_to(directory).as_posix()
            for name, relative in {
                "investigation": "phase1/investigation.json",
                "decision": "phase2/decision.json",
                "summary": "summary.json",
                "input_provenance": "input-provenance.json",
                "exact_wiki_reads": "phase1/turn-01/wiki-reads.json",
            }.items()
        }
        report["stages"]["assessment"] = {
            "mode": "mock",
            "validation": "passed",
            "provider": "fake",
            "model": "deterministic-fixture",
            "contract": "v1",
            "embedding": "component fake vectors; no downloaded model",
            "input_snapshot": "Original assessment fixture, NOT newly packaged memory bundle",
        }
        report["stages"]["collection"] = {"mode": "skipped", "reason": "Frozen evidence used"}
        report["stages"]["web"] = {
            "mode": "skipped",
            "reason": "Optional prepared-workspace consumer",
        }
        from .verification import inspect_provenance

        report["provenance"] = inspect_provenance(directory, artifacts, expectations)
        report["elapsed_seconds"] = round(monotonic() - started, 3)
        report["validation_passed"] = True
        (directory / "summary.md").write_text(
            "# VCLogic reviewer demonstration\n\n"
            f"Investor: {artifacts['investor']}; pitch: {artifacts['episode']}.\n\n"
            "Validation passed. Paid inference: **no**.\n\n"
            "- Memory: frozen, real validator passed.\n"
            "- Onboarding: recomputed and installed; valid but **not assessment-ready**.\n"
            "- Assessment: separate original v1 fixture; **scripted fake provider**.\n"
            "- Publication reproduction: **unavailable**, archive not supplied.\n\n"
            "These are separate input snapshots; this run does not demonstrate a continuous "
            "new-memory-to-live-assessment pipeline or scientific predictive accuracy.\n\n"
            "Inspect [report.json](report.json) for hashes, stage provenance and source locations. "
            "Rationale reconstruction and In/Out decision prediction are separate outcomes.\n"
        )
        report["files"] = inventory(directory)
        write_json(directory / "report.json", report)
        from .verification import verify_run

        verify_run(ctx, directory)
        write_json(ctx.workspace / "latest.json", {"run_directory": str(directory)})
        print(f"Validation passed; no paid inference. Outputs: {directory}", flush=True)
        return report
    except (ValueError, OSError, KeyError, TypeError) as error:
        report["validation_passed"] = False
        report["failed_stage"] = stage
        report["error"] = str(error)
        write_json(directory / "report.json", report)
        raise ValueError(
            f"Demo failed at {stage}: {error}; report: {directory / 'report.json'}"
        ) from error
