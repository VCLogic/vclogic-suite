from types import SimpleNamespace

import pytest

from vclogic_suite import data


def test_predictions_refuse_to_replace_the_installed_file(tmp_path):
    ctx = SimpleNamespace(workspace=tmp_path / "workspace", checkout=lambda _name: tmp_path)
    installed = ctx.workspace / "research/pipeline/proposal-evaluation/data/predictions.csv"
    installed.parent.mkdir(parents=True)
    installed.write_text("vc_id\n")

    with pytest.raises(ValueError, match="--force"):
        data.build_predictions(ctx, [tmp_path], None, force=False)
