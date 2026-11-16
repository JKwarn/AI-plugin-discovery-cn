import json
from pathlib import Path

from scripts.build.build_site import build_catalog, build_site


def test_catalog_contains_active_plugins_and_skills(data_dir):
    project_root = data_dir.parent.parent
    catalog = build_catalog(project_root)

    assert catalog["counts"]["plugins"] > 0
    assert catalog["counts"]["skills"] > 0
    assert all(skill["plugin_id"] in {p["id"] for p in catalog["plugins"]}
               for skill in catalog["skills"])


def test_build_site_copies_reviewed_translations(tmp_path, data_dir):
    project_root = data_dir.parent.parent
    output = tmp_path / "dist"
    catalog = build_site(project_root, output)

    assert (output / "index.html").is_file()
    assert (output / "assets" / "js" / "app.js").is_file()
    assert (output / "data" / "catalog.json").is_file()
    built = json.loads((output / "data" / "catalog.json").read_text(encoding="utf-8"))
    assert built["counts"] == catalog["counts"]
    for skill in catalog["skills"]:
        translation = skill.get("translation")
        if translation:
            assert (output / translation["path"]).is_file()


def test_build_refuses_project_root_as_output(tmp_path, data_dir):
    project_root = data_dir.parent.parent
    try:
        build_site(project_root, project_root)
    except ValueError as exc:
        assert "项目根目录" in str(exc)
    else:
        raise AssertionError("expected output path guard")
