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


def test_init_fetches_all_pins_and_installs_all(monkeypatch, tmp_path, capsys):
    from vclogic_suite import cli

    fetched, installed = [], []
    monkeypatch.setattr(
        cli, "ensure_component", lambda item, directory, **kw: fetched.append(item.id)
    )

    def install(ctx, profile, **kwargs):
        installed.append((profile, kwargs))
        return {"ready": True}

    monkeypatch.setattr(cli, "bootstrap", install)
    assert cli.main(["--root", str(ROOT), "--components-dir", str(tmp_path), "init"]) == 0
    assert len(fetched) == 5
    assert installed == [("all", {"offline": False})]
    assert json.loads(capsys.readouterr().out)["ready"]


def test_test_never_bootstraps_missing_installation(monkeypatch, tmp_path, capsys):
    from vclogic_suite import cli, demo

    def forbidden(*args, **kwargs):
        raise AssertionError("test must not fetch or install")

    monkeypatch.setattr(demo, "bootstrap", forbidden)
    assert cli.main(["--root", str(ROOT), "--components-dir", str(tmp_path), "test"]) == 1
    assert "vclogic init" in capsys.readouterr().err


def test_init_allows_tailored_profiles():
    from vclogic_suite.cli import parser

    for profile in ("core", "web", "all"):
        assert parser().parse_args(["init", "--profile", profile]).profile == profile
