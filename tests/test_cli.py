import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-m", "vclogic_suite.cli", "--root", str(ROOT), *args],
        text=True,
        capture_output=True,
    )


def test_components_lists_all_five_pinned_revisions():
    result = invoke("components")
    assert result.returncode == 0, result.stderr
    rows = json.loads(result.stdout)["components"]
    assert len(rows) == 5
    assert all(len(row["commit"]) == 40 for row in rows)


def test_missing_report_is_actionable(tmp_path):
    result = invoke("verify", "--run", str(tmp_path / "absent"))
    assert result.returncode == 1
    assert "report" in result.stderr.lower()
    assert "Traceback" not in result.stderr


def test_cli_help_lists_public_commands():
    result = invoke("--help")
    assert result.returncode == 0
    for command in ("init", "test", "demo", "bootstrap", "verify", "doctor", "web", "assess"):
        assert command in result.stdout


def test_init_fetches_all_pins_without_installing_environments(monkeypatch, tmp_path, capsys):
    from vclogic_suite import cli

    fetched = []
    def fetch(item, directory, **kw):
        fetched.append((item, directory, kw))

    def unexpected_install(*args, **kwargs):
        raise AssertionError("init must only fetch")

    monkeypatch.setattr(cli, "ensure_component", fetch)
    monkeypatch.setattr(cli, "bootstrap", unexpected_install)
    assert cli.main(["--root", str(ROOT), "--components-dir", str(tmp_path), "init", "--offline"]) == 0
    assert len(fetched) == 5
    assert all(directory == tmp_path and kw == {"offline": True} for _, directory, kw in fetched)
    assert len(json.loads(capsys.readouterr().out)["components"]) == 5


def test_test_runs_reviewer_validations_and_propagates_failure(monkeypatch, capsys):
    from vclogic_suite import cli, demo

    def fail(ctx, *, offline):
        assert offline is True
        raise ValueError("fixture validation failed")

    monkeypatch.setattr(demo, "demo", fail)
    assert cli.main(["--root", str(ROOT), "test", "--offline"]) == 1
    assert "fixture validation failed" in capsys.readouterr().err
