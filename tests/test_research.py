import argparse

import pytest


def test_missing_provider_key_is_named_without_value(tmp_path, monkeypatch):
    from vclogic_suite.research import check_credentials

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        check_credentials({"provider": {"kind": "openrouter"}})


def test_fake_research_provider_rejected():
    from vclogic_suite.research import check_credentials

    with pytest.raises(ValueError, match="fixture"):
        check_credentials({"provider": {"kind": "fake"}})


def test_web_without_installed_investor_is_actionable(tmp_path):
    from vclogic_suite.research import launch
    from vclogic_suite.runtime import Context

    ctx = Context(tmp_path, tmp_path / "components", tmp_path / "outputs")
    (ctx.workspace / "research/pipeline").mkdir(parents=True)
    args = argparse.Namespace(command="web", research_workspace=None, config=None, investor=None)
    with pytest.raises(ValueError, match="vclogic run"):
        launch(ctx, args)
