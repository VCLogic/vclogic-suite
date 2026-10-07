import argparse

import pytest


def test_live_operations_require_explicit_opt_in_before_bootstrap(tmp_path):
    from vclogic_suite.research import launch
    from vclogic_suite.runtime import Context

    ctx = Context(tmp_path, tmp_path / "components", tmp_path / "outputs")
    args = argparse.Namespace(command="assess", allow_paid=False)
    with pytest.raises(ValueError, match="allow-paid"):
        launch(ctx, args)


def test_missing_provider_key_is_named_without_value(tmp_path, monkeypatch):
    from vclogic_suite.research import check_credentials

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        check_credentials({"provider": {"kind": "openrouter"}})


def test_fake_research_provider_rejected():
    from vclogic_suite.research import check_credentials

    with pytest.raises(ValueError, match="fixture"):
        check_credentials({"provider": {"kind": "fake"}})
