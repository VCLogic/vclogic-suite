import json
import subprocess

import pytest


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


@pytest.fixture
def repository(tmp_path):
    remote = tmp_path / "remote"
    remote.mkdir()
    git(remote, "init", "-q")
    git(remote, "config", "user.email", "test@example.invalid")
    git(remote, "config", "user.name", "Fixture")
    (remote / "data.txt").write_text("frozen\n")
    git(remote, "add", ".")
    git(remote, "commit", "-qm", "fixture")
    return remote, git(remote, "rev-parse", "HEAD")


def test_fetch_exact_commit_idempotent_and_refuse_drift(repository, tmp_path):
    from vclogic_suite.components import Component, ensure_component, verify_component

    remote, sha = repository
    component = Component("example", str(remote), sha, "example", "example", "1", "fixture")
    destination = ensure_component(component, tmp_path / "components")
    assert git(destination, "rev-parse", "HEAD") == sha
    assert ensure_component(component, tmp_path / "components") == destination
    (destination / "data.txt").write_text("changed")
    with pytest.raises(ValueError, match="modified"):
        verify_component(component, tmp_path / "components")
    with pytest.raises(ValueError, match="modified"):
        ensure_component(component, tmp_path / "components")


def test_wrong_origin_and_missing_offline_are_rejected(repository, tmp_path):
    from vclogic_suite.components import Component, ensure_component, verify_component

    remote, sha = repository
    component = Component("example", str(remote), sha, "example", "example", "1", "fixture")
    with pytest.raises(ValueError, match="offline"):
        ensure_component(component, tmp_path / "components", offline=True)
    target = ensure_component(component, tmp_path / "components")
    git(target, "remote", "set-url", "origin", "https://example.invalid/other.git")
    with pytest.raises(ValueError, match="origin"):
        verify_component(component, tmp_path / "components")


def test_manifest_rejects_branch_and_path_escape(tmp_path):
    from vclogic_suite.components import load_components

    row = dict(
        id="bad",
        repository="https://github.com/VCLogic/example.git",
        commit="main",
        directory="../outside",
        package="example",
        version="1",
        role="fixture",
    )
    file = tmp_path / "lock.json"
    file.write_text(json.dumps({"schema_version": 1, "components": [row]}))
    with pytest.raises(ValueError):
        load_components(file)


def test_fetch_rejects_symlink_destination(repository, tmp_path):
    from vclogic_suite.components import Component, ensure_component

    remote, sha = repository
    component = Component("example", str(remote), sha, "example", "example", "1", "fixture")
    root = tmp_path / "components"
    root.mkdir()
    (root / "example").symlink_to(remote, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        ensure_component(component, root)
