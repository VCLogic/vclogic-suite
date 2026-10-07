import os
from pathlib import Path

import pytest

from vclogic_suite.cli import parser
from vclogic_suite.runtime import Context


def test_root_env_precedence_restoration_and_literal_values(tmp_path, monkeypatch):
    from vclogic_suite.environment import research_environment

    monkeypatch.setenv("OPENAI_API_KEY", "shell-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        'OPENAI_API_KEY=file-key\nOPENROUTER_API_KEY="literal-${HOME}"\n'
    )
    with research_environment(tmp_path):
        assert os.environ["OPENAI_API_KEY"] == "shell-key"
        assert os.environ["OPENROUTER_API_KEY"] == "literal-${HOME}"
    assert "OPENROUTER_API_KEY" not in os.environ
    assert os.environ["OPENAI_API_KEY"] == "shell-key"


def test_process_handoff_and_failure_stop(tmp_path, monkeypatch):
    from vclogic_suite import workflow

    calls = []

    def invoke(ctx, component, command, *, cwd):
        calls.append((component, command, cwd))
        return 4 if command[1] == "export" else 0

    monkeypatch.setattr(workflow, "invoke", invoke)
    ctx = Context(tmp_path, tmp_path / "components", tmp_path / "workspace")
    args = parser().parse_args(["process", "--investor", "example-vc"])
    assert workflow.run_stage(ctx, args) == 4
    assert [c[1][1] for c in calls] == ["process", "export"]
    assert all(str(ctx.workspace / "research/traces") in c[1] for c in calls)


def test_workflow_rejects_path_escape(tmp_path):
    from vclogic_suite.workflow import run_stage

    ctx = Context(tmp_path, tmp_path / "components", tmp_path / "workspace")
    args = parser().parse_args(["memory", "--investor", "../escape", "--allow-paid"])
    with pytest.raises(ValueError, match="slug"):
        run_stage(ctx, args)


def test_memory_requires_explicit_generation_opt_in(tmp_path):
    from vclogic_suite.workflow import run_stage

    ctx = Context(tmp_path, tmp_path / "components", tmp_path / "workspace")
    args = parser().parse_args(["memory", "--investor", "example-vc"])
    with pytest.raises(ValueError, match="allow-paid"):
        run_stage(ctx, args)


def test_rejects_overridden_output_paths(tmp_path):
    from vclogic_suite.workflow import run_stage

    ctx = Context(tmp_path, tmp_path / "components", tmp_path / "workspace")
    args = parser().parse_args(
        ["process", "--investor", "example", "--", "--output-dir=/tmp/wrong"]
    )
    with pytest.raises(ValueError, match="suite manages"):
        run_stage(ctx, args)


def test_no_key_command_does_not_load_root_env(tmp_path, monkeypatch):
    from vclogic_suite import cli

    monkeypatch.delenv("SUITE_ENV_SENTINEL", raising=False)
    (tmp_path / ".env").write_text("SUITE_ENV_SENTINEL=secret\n")
    (tmp_path / "manifests").mkdir()
    source = Path(__file__).resolve().parents[1] / "manifests/components.lock.json"
    (tmp_path / "manifests/components.lock.json").write_bytes(source.read_bytes())
    assert cli.main(["--root", str(tmp_path), "components"]) == 0
    assert "SUITE_ENV_SENTINEL" not in os.environ


def test_init_embeddings_is_explicit():
    assert parser().parse_args(["init", "--embeddings"]).embeddings is True
    assert parser().parse_args(["init"]).embeddings is False


def test_assess_can_use_managed_workspace():
    args = parser().parse_args(
        ["assess", "--investor", "example", "--pitch", "pitch.txt", "--allow-paid"]
    )
    assert args.research_workspace is None
    assert args.config is None


def test_cli_research_inherits_env_and_restores_after_failure(tmp_path, monkeypatch):
    from vclogic_suite import cli, workflow

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fixture-secret\n")
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests/components.lock.json").write_text("{}")

    def run(ctx, args):
        assert os.environ["OPENROUTER_API_KEY"] == "fixture-secret"
        assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"
        return 4

    monkeypatch.setattr(workflow, "run_stage", run)
    assert cli.main(["--root", str(tmp_path), "collect", "--investor", "example"]) == 4
    assert "OPENROUTER_API_KEY" not in os.environ


def test_partial_onboarding_reports_readiness_and_installs(tmp_path, monkeypatch, capsys):
    from vclogic_suite import workflow

    calls = []

    def invoke(ctx, component, command, *, cwd):
        calls.append(command)
        return 0

    monkeypatch.setattr(workflow, "invoke", invoke)
    monkeypatch.setattr(
        workflow,
        "component_command",
        lambda *a, **kw: '{"valid":true,"ready_for_assessment":false}',
    )
    ctx = Context(tmp_path, tmp_path / "components", tmp_path / "workspace")
    args = parser().parse_args(["onboard", "--investor", "example", "--skip-indexes"])
    assert workflow.run_stage(ctx, args) == 0
    assert [call[1] for call in calls] == ["prepare", "install"]
    assert str(ctx.workspace / "research/wiki/example") in calls[0]
    assert str(ctx.workspace / "research/pipeline") in calls[1]
    assert '"ready_for_assessment": false' in capsys.readouterr().out
    calls.clear()
    args.skip_indexes = False
    with pytest.raises(ValueError, match="not assessment-ready"):
        workflow.run_stage(ctx, args)
    assert len(calls) == 1  # No installation after readiness failure.


def test_pipeline_stops_on_preflight_failure(tmp_path, monkeypatch):
    from vclogic_suite import workflow

    root = tmp_path / "research/pipeline"
    root.mkdir(parents=True)
    (root / "native.toml").write_text('[run]\nvc_slug="example"\n[provider]\nkind="ollama"\n')
    calls = []

    def invoke(ctx, component, command, *, cwd):
        assert cwd == root
        calls.append(command)
        return 1

    monkeypatch.setattr(workflow, "invoke", invoke)
    ctx = Context(tmp_path, tmp_path / "components", tmp_path)
    args = parser().parse_args(
        ["pipeline", "--investor", "example", "--config", "native.toml", "--allow-paid"]
    )
    assert workflow.run_stage(ctx, args) == 1
    assert [c[1] for c in calls] == ["preflight"]


def test_bootstrap_upgrades_cached_environments_with_embedding_extras(tmp_path, monkeypatch):
    from vclogic_suite import runtime
    from vclogic_suite.files import write_json

    stamp = {"fixture": "pinned"}

    class FixtureContext:
        workspace = tmp_path
        components_dir = tmp_path
        components = {name: name for name in runtime.CORE}

        def checkout(self, name):
            return tmp_path / name

    ctx = FixtureContext()
    for name in ("assessment", "onboarding"):
        write_json(ctx.checkout(name) / ".venv/vclogic-suite-environment.json", stamp)
    monkeypatch.setattr(runtime, "ensure_component", lambda *a, **kw: None)
    monkeypatch.setattr(runtime, "environment_stamp", lambda *a: stamp)
    monkeypatch.setattr(runtime.shutil, "which", lambda name: name)
    commands = []
    monkeypatch.setattr(runtime, "run", lambda command, **kw: commands.append(command))
    runtime.bootstrap(ctx, embeddings=True)
    assert len(commands) == 2
    assert all(command[-2:] == ["--extra", "embeddings"] for command in commands)
    runtime.bootstrap(ctx, embeddings=True)
    assert len(commands) == 2  # Reuse matching installation receipts.


def test_no_key_environment_disables_component_dotenv(monkeypatch):
    from vclogic_suite.runtime import execution_environment

    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "0")
    assert execution_environment(no_keys=True)["PYTHON_DOTENV_DISABLED"] == "1"
