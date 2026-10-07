"""Run component-owned validators and audit source links in their artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from .files import digest, safe_path, verify_files
from .runtime import CORE, Context, component_command


def inspect_provenance(directory: Path, artifacts: dict, expectations: dict) -> dict:
    workspace = directory / "assessment-workspace"
    output = workspace / "outputs/fake-elizabeth-thoras" / artifacts["episode"]
    investigation = json.loads((output / "phase1/investigation.json").read_text())
    decision = json.loads((output / "phase2/decision.json").read_text())
    rationales = investigation.get("rationales")
    if not rationales or any(
        not set(expectations["rationale_required_fields"]) <= set(row) for row in rationales
    ):
        raise ValueError("Assessment lacks required rationale/evidence fields")
    if not set(expectations["decision_required_fields"]) <= set(decision):
        raise ValueError("Assessment lacks required decision fields")
    if decision.get("decision") not in expectations["allowed_decisions"]:
        raise ValueError("Assessment lacks In/Out decision")
    if decision.get("investigation_sha256") != digest(output / "phase1/investigation.json"):
        raise ValueError("Decision does not bind investigation hash")
    if not set(decision.get("controlling_rationale_ids", [])) <= {
        r["rationale_id"] for r in rationales
    }:
        raise ValueError("Decision references unknown rationale")
    reads = json.loads((output / "phase1/turn-01/wiki-reads.json").read_text())
    cited = {value for row in rationales for value in row["wiki_evidence_ids"]}
    reads_by_id = {row["chunk_id"]: row for row in reads}
    if not cited or not cited <= reads_by_id.keys():
        raise ValueError("Rationale citations have no exact evidence reads")
    sources = []
    wiki = workspace / "inputs/wiki" / artifacts["investor"]
    for evidence_id in sorted(cited):
        row = reads_by_id[evidence_id]
        source = safe_path(wiki, row["source_path"])
        if not row["text"] or digest(source) != row["source_sha256"]:
            raise ValueError("Evidence source hash mismatch")
        sources.append(
            {
                "evidence_id": evidence_id,
                "path": source.relative_to(directory).as_posix(),
                "sha256": row["source_sha256"],
            }
        )
    return {
        "cited_wiki_evidence_ids": sorted(cited),
        "sources": sources,
        "note": "Follow [ev:...] citations in exact reads to the frozen assessment wiki sources.",
    }


def verify_run(ctx: Context, directory: Path | None = None) -> dict:
    if directory is None:
        pointer = ctx.workspace / "latest.json"
        if not pointer.is_file():
            raise ValueError("No demo report found; run vclogic demo first")
        directory = Path(json.loads(pointer.read_text())["run_directory"])
    directory = directory.resolve()
    report_path = directory / "report.json"
    if not report_path.is_file():
        raise ValueError(f"No demo report at {report_path}")
    report = json.loads(report_path.read_text())
    if (
        report.get("schema_version") != "vclogic-suite-demo-v1"
        or report.get("validation_passed") is not True
    ):
        raise ValueError("Demo report does not describe a successful supported run")
    if report.get("paid_inference") is not False:
        raise ValueError("Reviewer demo must not report paid inference")
    for field, file in [
        ("components_manifest_sha256", "components.lock.json"),
        ("artifacts_manifest_sha256", "reviewer-artifacts.json"),
    ]:
        if report.get(field) != digest(ctx.root / "manifests" / file):
            raise ValueError("Demo report manifest hash differs from this suite version")
    expected_path = ctx.root / "expected_outputs/reviewer-demo/contract.json"
    if report.get("expectations_sha256") != digest(expected_path):
        raise ValueError("Demo expectations hash differs from this suite version")
    expectations = json.loads(expected_path.read_text())
    stages = report.get("stages", {})
    if stages.get("onboarding", {}).get("ready_for_assessment") is not False:
        raise ValueError("Incorrect onboarding readiness claim")
    if (
        stages.get("assessment", {}).get("mode") != "mock"
        or stages["assessment"].get("provider") != expectations["assessment_provider"]
        or stages["assessment"].get("contract") != expectations["component_contract"]
        or report.get("publication", {}).get("status") != expectations["publication_status"]
    ):
        raise ValueError("Incorrect reviewer stage or publication claims")
    for name in CORE:
        ctx.checkout(name)
        if report["components"].get(name) != ctx.components[name].commit:
            raise ValueError("Demo report component revision mismatch")
    verify_files(directory, report["files"])
    artifacts = json.loads((ctx.root / "manifests/reviewer-artifacts.json").read_text())
    verify_files(directory / "frozen-memory", artifacts["memory"]["files"])
    verify_files(directory / "assessment-workspace", artifacts["assessment"]["files"])
    checks = [
        (
            "onboarding",
            [
                "investor-memory",
                "check",
                str(directory / "frozen-memory" / artifacts["memory"]["path"]),
            ],
        ),
        (
            "onboarding",
            ["investor-onboarding", "check", "--bundle", str(directory / "onboarding-bundle")],
        ),
    ]
    for component, args in checks:
        result = json.loads(component_command(ctx, component, args, cwd=directory))
        if result.get("valid") is not True:
            raise ValueError(f"{args[0]} validation failed")
        if args[0] == "investor-onboarding" and (
            result.get("ready_for_assessment")
            is not expectations["onboarding_ready_for_assessment"]
            or result.get("capabilities") != stages["onboarding"].get("capabilities")
        ):
            raise ValueError("Onboarding readiness/capabilities differ from report")
    component_command(
        ctx,
        "assessment",
        ["vc-clone-graph", "verify", "--config", artifacts["assessment"]["config"]],
        cwd=directory / "assessment-workspace",
    )
    provenance = inspect_provenance(directory, artifacts, expectations)
    if provenance != report["provenance"]:
        raise ValueError("Reported provenance differs from verified artifacts")
    return {
        "valid": True,
        "run_directory": str(directory),
        "paid_inference": False,
        "publication_reproduction": "unavailable",
    }
