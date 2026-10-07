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
    for command in ("demo", "bootstrap", "verify", "doctor", "web", "assess"):
        assert command in result.stdout
