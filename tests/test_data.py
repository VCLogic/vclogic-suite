from types import SimpleNamespace

import pytest

from vclogic_suite import data


def _bundle(root):
    for path, text in {
        "configs/investors/ada/rehearsal.toml": "[run]\n",
        "inputs/investors/ada.toml": "slug = 'ada'\n",
        "proposal-evaluation/data/predictions.csv": "vc_id\n",
        "configs/desktop.ini": "[.ShellClassInfo]\n",
        "research/cases.csv": "case\n",
    }.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def _ctx(tmp_path):
    assessment = tmp_path / "assessment"
    (assessment / "inputs/taxonomy").mkdir(parents=True)
    (assessment / "inputs/taxonomy/codebook_v_final.json").write_text("[]")
    return SimpleNamespace(workspace=tmp_path / "workspace", checkout=lambda _name: assessment)


def test_install_copies_the_runtime_part_and_reruns_cleanly(tmp_path):
    ctx, bundle = _ctx(tmp_path), _bundle(tmp_path / "bundle")

    first = data.install_data(ctx, bundle)
    again = data.install_data(ctx, bundle)

    target = ctx.workspace / "research/pipeline"
    assert first["copied_files"] == 3 and first["taxonomy_added"] and first["investors"] == ["ada"]
    assert (target / "proposal-evaluation/data/predictions.csv").is_file()
    assert (target / "inputs/taxonomy/codebook_v_final.json").is_file()
    assert not (target / "configs/desktop.ini").exists()
    assert not (target / "research").exists()
    assert again["copied_files"] == 0 and again["already_present"] == 3


def test_install_never_overwrites_a_different_file(tmp_path):
    ctx, bundle = _ctx(tmp_path), _bundle(tmp_path / "bundle")
    existing = ctx.workspace / "research/pipeline/inputs/investors/ada.toml"
    existing.parent.mkdir(parents=True)
    existing.write_text("slug = 'mine'\n")

    with pytest.raises(ValueError, match="nothing was copied"):
        data.install_data(ctx, bundle)

    assert existing.read_text() == "slug = 'mine'\n"
    assert not (ctx.workspace / "research/pipeline/configs").exists()


def test_install_rejects_a_folder_that_is_not_a_bundle(tmp_path):
    with pytest.raises(ValueError, match="Not a VCLogic data bundle"):
        data.install_data(_ctx(tmp_path), tmp_path)


def test_predictions_refuse_to_replace_the_installed_file(tmp_path):
    ctx = _ctx(tmp_path)
    installed = ctx.workspace / "research/pipeline/proposal-evaluation/data/predictions.csv"
    installed.parent.mkdir(parents=True)
    installed.write_text("vc_id\n")

    with pytest.raises(ValueError, match="--force"):
        data.build_predictions(ctx, [tmp_path], None, force=False)
