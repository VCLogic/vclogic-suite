"""Real component subprocess tests; setup explicitly in CI or with bootstrap."""

import json
import os
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("VCLOGIC_INTEGRATION") != "1",
        reason="Run bootstrap, then VCLOGIC_INTEGRATION=1 uv run pytest",
    ),
]


def test_real_offline_demo_and_tamper_detection(tmp_path, monkeypatch):
    from vclogic_suite.demo import demo
    from vclogic_suite.runtime import Context
    from vclogic_suite.verification import verify_run

    root = Path(__file__).resolve().parents[2]
    ctx = Context(root, root / ".components", tmp_path / "workspace")
    monkeypatch.setenv("OPENROUTER_API_KEY", "SENTINEL-MUST-NOT-APPEAR")
    report = demo(ctx, offline=True)
    run = Path(report["run_directory"])
    assert report["validation_passed"] is True
    assert report["paid_inference"] is False
    assert report["publication"]["status"] == "unavailable"
    assert report["stages"]["onboarding"]["ready_for_assessment"] is False
    assert report["stages"]["assessment"]["mode"] == "mock"
    assert verify_run(ctx, run)["valid"] is True
    saved = (run / "report.json").read_text()
    dishonest = json.loads(saved)
    dishonest["stages"]["onboarding"]["ready_for_assessment"] = True
    (run / "report.json").write_text(json.dumps(dishonest))
    with pytest.raises(ValueError, match="readiness"):
        verify_run(ctx, run)
    (run / "report.json").write_text(saved)
    assert report["provenance"]["cited_wiki_evidence_ids"]
    for file in run.rglob("*"):
        if file.is_file() and file.suffix in {".json", ".log", ".md"}:
            assert "SENTINEL-MUST-NOT-APPEAR" not in file.read_text()
    decision = run / report["outputs"]["decision"]
    decision.write_text("{}")
    with pytest.raises(ValueError, match="hash"):
        verify_run(ctx, run)


def test_probe_uses_native_embedding_identity_without_loading_models():
    from vclogic_suite.runtime import Context, component_command

    root = Path(__file__).resolve().parents[2]
    ctx = Context(root, root / ".components", root / "workspace")
    code = """
import sys
sys.path.insert(0, sys.argv[1])
from vclogic_suite.research_probe import offline_embedding_identity
from vc_clone_graph.config import EmbeddingSettings
from vc_clone_graph.providers.ollama import OllamaProvider
from vc_clone_graph.providers.base import embedding_identity
settings = EmbeddingSettings(kind="ollama", model="fixture", base_url="http://127.0.0.1:1")
actual = OllamaProvider("embedding-only", "fixture", client=object())
assert offline_embedding_identity(settings).metadata == embedding_identity(actual)
assert offline_embedding_identity(settings).metadata["normalize"] is False
assert offline_embedding_identity(settings).metadata["query_prefix"] == ""
settings = EmbeddingSettings(kind="sentence_transformers", model="not-downloaded", revision="a" * 40)
assert offline_embedding_identity(settings).metadata["revision"] == "a" * 40
print("native identity matched; no model loaded")
"""
    output = component_command(
        ctx, "assessment", ["python", "-c", code, str(root / "src")], cwd=root
    )
    assert "native identity matched" in output
