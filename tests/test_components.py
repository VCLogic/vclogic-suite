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


def test_clean_checkout_moves_to_new_pin(repository, tmp_path):
    from vclogic_suite.components import Component, ensure_component

    remote, sha = repository
    component = Component("example", str(remote), sha, "example", "example", "1", "fixture")
    destination = ensure_component(component, tmp_path / "components")
    (remote / "data.txt").write_text("updated\n")
    git(remote, "commit", "-qam", "update")
    newer = git(remote, "rev-parse", "HEAD")
    git(remote, "config", "uploadpack.allowReachableSHA1InWant", "true")
    moved = Component("example", str(remote), newer, "example", "example", "1", "fixture")
    assert ensure_component(moved, tmp_path / "components") == destination
    assert (destination / "data.txt").read_text() == "updated\n"
    with pytest.raises(ValueError, match="Wrong revision"):
        # Offline never fetches; a stale pin is reported, not silently used.
        ensure_component(component, tmp_path / "components", offline=True)


def test_sparse_checkout_holds_only_listed_files_and_stays_clean(tmp_path):
    from vclogic_suite.components import Component, ensure_component, verify_component

    remote = tmp_path / "remote"
    deep = remote / ("d" * 120) / ("e" * 120)
    deep.mkdir(parents=True)
    (deep / "too-long-for-windows.json").write_text("{}")
    (remote / "keep").mkdir()
    (remote / "keep/data.txt").write_text("frozen\n")
    git(remote, "init", "-q")
    git(remote, "config", "user.email", "test@example.invalid")
    git(remote, "config", "user.name", "Fixture")
    git(remote, "add", ".")
    git(remote, "commit", "-qm", "fixture")
    sha = git(remote, "rev-parse", "HEAD")
    component = Component("example", str(remote), sha, "example", "example", "1", "fixture")
    target = ensure_component(component, tmp_path / "components", paths=["keep/data.txt"])
    assert sorted(p.name for p in target.iterdir()) == [".git", "keep"]
    assert (target / "keep/data.txt").read_text() == "frozen\n"
    assert verify_component(component, tmp_path / "components") == target


def test_claude_skill_copy_matches_agents_skill():
    # A real copy, not a symlink: Git on Windows checks symlinks out as text files.
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source, copy = root / ".agents/skills/vclogic", root / ".claude/skills/vclogic"
    assert not copy.is_symlink()
    names = sorted(p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file())
    assert names == sorted(p.relative_to(copy).as_posix() for p in copy.rglob("*") if p.is_file())
    for name in names:
        assert (source / name).read_bytes() == (copy / name).read_bytes(), name


def test_suite_uv_cache_reaches_components_with_own_uv_config(tmp_path, monkeypatch):
    import os

    from vclogic_suite.runtime import share_uv_cache

    monkeypatch.delenv("UV_CACHE_DIR", raising=False)
    (tmp_path / "uv.toml").write_text(f'cache-dir = "{(tmp_path / "cache").as_posix()}"\n')
    share_uv_cache(tmp_path)
    assert os.environ["UV_CACHE_DIR"] == str(tmp_path / "cache")
