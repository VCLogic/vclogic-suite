from hashlib import sha256

import pytest


def test_copy_manifest_checks_hashes_and_refuses_escape(tmp_path):
    from vclogic_suite.files import copy_verified

    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir()
    (source / "evidence.json").write_text("source")
    hashes = {"evidence.json": sha256(b"source").hexdigest()}
    copy_verified(source, target, hashes)
    assert (target / "evidence.json").read_text() == "source"
    (source / "evidence.json").write_text("changed")
    with pytest.raises(ValueError, match="hash"):
        copy_verified(source, tmp_path / "other", hashes)
    with pytest.raises(ValueError, match="path"):
        copy_verified(source, tmp_path / "escape", {"../outside": "a" * 64})


def test_symlink_artifact_rejected(tmp_path):
    from vclogic_suite.files import copy_verified

    source = tmp_path / "source"
    source.mkdir()
    (tmp_path / "secret").write_text("secret")
    (source / "link").symlink_to(tmp_path / "secret")
    with pytest.raises(ValueError, match="symlink"):
        copy_verified(source, tmp_path / "out", {"link": sha256(b"secret").hexdigest()})


def test_no_key_environment_strips_credentials_and_python_overrides(monkeypatch):
    from vclogic_suite.runtime import execution_environment

    for name in ("OPENAI_API_KEY", "HF_TOKEN", "AZURE_SECRET", "PYTHONPATH", "VIRTUAL_ENV"):
        monkeypatch.setenv(name, "do-not-leak")
    env = execution_environment(no_keys=True)
    assert "OPENAI_API_KEY" not in env
    assert "HF_TOKEN" not in env
    assert "AZURE_SECRET" not in env
    assert "PYTHONPATH" not in env
    assert "VIRTUAL_ENV" not in env
    assert env["HF_HUB_OFFLINE"] == "1"


def test_web_command_checks_editable_assessment_dependency(tmp_path):
    from vclogic_suite.runtime import component_command

    class Context:
        def checkout(self, name):
            if name == "assessment":
                raise ValueError("Component assessment is modified")
            return tmp_path

    (tmp_path / ".venv").mkdir()
    with pytest.raises(ValueError, match="assessment is modified"):
        component_command(Context(), "web", ["python", "-c", "pass"], cwd=tmp_path)
