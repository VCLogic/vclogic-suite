from types import SimpleNamespace

from vclogic_suite import runtime
from vclogic_suite.files import write_json


def test_full_setup_upgrades_caches_and_reports_missing_host_tools(tmp_path, monkeypatch):
    class FixtureContext:
        root = tmp_path
        workspace = tmp_path / "workspace"
        components_dir = tmp_path / "components"
        components = {name: SimpleNamespace(commit="a" * 40) for name in runtime.PROFILES["all"]}

        def checkout(self, name):
            path = self.components_dir / name
            path.mkdir(parents=True, exist_ok=True)
            return path

    ctx = FixtureContext()
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/memory-pdf.lock").write_text("pypdf==6.19.0\n")
    frontend = ctx.checkout("web") / "web/frontend"
    (frontend / "dist").mkdir(parents=True)
    (frontend / "dist/index.html").write_text("fixture")
    (frontend / "package-lock.json").write_text("{}")
    stamp = {"fixture": "locked"}
    for name in runtime.PROFILES["all"]:
        write_json(ctx.checkout(name) / ".venv/vclogic-suite-environment.json", stamp)
    monkeypatch.setattr(runtime, "ensure_component", lambda *a, **kw: None)
    monkeypatch.setattr(runtime, "environment_stamp", lambda *a: stamp)
    monkeypatch.setattr(
        runtime.shutil, "which", lambda name: None if name == "agent-reach" else name
    )
    calls = []
    monkeypatch.setattr(runtime, "run", lambda command, **kw: calls.append((command, kw)))
    report = runtime.bootstrap(ctx, "all", full=True)
    assert report["ready"] is False
    assert set(report["missing_prerequisites"]) == {"agent-reach"}
    syncs = {kw["cwd"].name: command for command, kw in calls if command[:2] == ["uv", "sync"]}
    assert len(syncs) == 4
    for name, extras in runtime.FULL_EXTRAS.items():
        for extra in extras:
            position = syncs[name].index(extra)
            assert syncs[name][position - 1] == "--extra"
    assert any(
        command[:3] == ["uv", "pip", "install"] and "--require-hashes" in command
        for command, _ in calls
    )
    assert any(command[-3:] == ["playwright", "install", "chromium"] for command, _ in calls)
    calls.clear()
    runtime.bootstrap(ctx, "all", full=True, offline=True)
    assert not any(command[:2] == ["uv", "sync"] for command, _ in calls)
    assert not any("install" in command for command, _ in calls)
