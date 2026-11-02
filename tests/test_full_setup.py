import json
from types import SimpleNamespace

import pytest

from vclogic_suite import runtime
from vclogic_suite.files import write_json


@pytest.mark.parametrize("shell,expected", [(None, True), ("cpu", False), ("cuda", True)])
def test_cuda_setting_uses_root_dotenv_with_shell_precedence(
    tmp_path, monkeypatch, shell, expected
):
    (tmp_path / ".env").write_text("VC_TRACE_AV_DEVICE=cuda\n")
    monkeypatch.delenv("VC_TRACE_AV_DEVICE", raising=False)
    if shell is not None:
        monkeypatch.setenv("VC_TRACE_AV_DEVICE", shell)
    assert runtime.cuda_requested(tmp_path) is expected


@pytest.mark.parametrize("compiled", [None, "13.0"])
def test_cuda_setup_preserves_versions_and_verifies_gpu(tmp_path, monkeypatch, compiled):
    calls = []
    versions = {"torch": "2.14.0+cpu", "torchaudio": "2.14.0+cpu"}

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if len(calls) == 1:
            return json.dumps({"versions": versions, "cuda": compiled})
        return ""

    monkeypatch.setattr(runtime, "run", run)
    ctx = SimpleNamespace(root=tmp_path, workspace=tmp_path)
    runtime.ensure_cuda(ctx, tmp_path / "component", offline=True)
    installs = [c for c, _ in calls if c[:3] == ["uv", "pip", "install"]]
    assert len(installs) == (compiled is None)
    if installs:
        command = installs[0]
        assert "torch==2.14.0" in command and "torchaudio==2.14.0" in command
        assert command[command.index("--torch-backend") + 1] == "auto"
        assert "--offline" in command
        assert command.count("--reinstall-package") == 2
    assert "device='cuda'" in calls[-1][0][-1]


def test_cuda_setup_does_not_add_torch_to_lightweight_environment(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return json.dumps({"versions": {}, "cuda": None})

    monkeypatch.setattr(runtime, "run", run)
    runtime.ensure_cuda(SimpleNamespace(root=tmp_path, workspace=tmp_path), tmp_path, offline=False)
    assert len(calls) == 1


def test_cuda_verification_failure_is_not_silently_accepted(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            return json.dumps({"versions": {"torch": "2.14.0+cu130"}, "cuda": "13.0"})
        raise ValueError("CUDA check failed")

    monkeypatch.setattr(runtime, "run", run)
    with pytest.raises(ValueError, match="CUDA check failed"):
        runtime.ensure_cuda(
            SimpleNamespace(root=tmp_path, workspace=tmp_path), tmp_path, offline=True
        )


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
    monkeypatch.setattr(runtime, "fetch_fixtures", lambda *a, **kw: None)
    monkeypatch.setattr(runtime, "environment_stamp", lambda *a: stamp)
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None if name == "mcporter" else name)
    calls = []
    monkeypatch.setattr(runtime, "run", lambda command, **kw: calls.append((command, kw)))
    report = runtime.bootstrap(ctx, "all", full=True)
    assert report["ready"] is False
    assert set(report["missing_prerequisites"]) == {"mcporter"}
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
    cuda_checks = []
    monkeypatch.setattr(
        runtime, "ensure_cuda", lambda ctx, project, **kw: cuda_checks.append(project.name)
    )
    runtime.bootstrap(ctx, "all", full=True, offline=True, cuda=True)
    assert set(cuda_checks) == {"assessment", "onboarding", "web", "collector"}
    assert not any(command[:2] == ["uv", "sync"] for command, _ in calls)



def test_long_path_leaves_other_platforms_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    assert runtime.long_path(tmp_path) == tmp_path


# Only Windows paths understand the \\?\ prefix, so this cannot be faked elsewhere.
@pytest.mark.skipif(runtime.sys.platform != "win32", reason="Windows path semantics")
def test_long_path_prefixes_windows_paths_once(tmp_path):
    prefixed = runtime.long_path(tmp_path)
    assert str(prefixed).startswith("\\\\?\\")
    assert runtime.long_path(prefixed) == prefixed
