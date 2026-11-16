import json
from pathlib import Path

from scripts.build.build_site import build_catalog, build_site


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_catalog_contains_active_plugins_and_skills():
    catalog = build_catalog(PROJECT_ROOT)

    assert catalog["counts"]["plugins"] > 0
    assert catalog["counts"]["skills"] > 0
    plugin_ids = {plugin["id"] for plugin in catalog["plugins"]}
    assert all(skill["plugin_id"] in plugin_ids for skill in catalog["skills"])


def test_catalog_taxonomy_nodes_retain_their_dimension():
    catalog = build_catalog(PROJECT_ROOT)

    for dimension, nodes in catalog["taxonomy"].items():
        assert all(node["dimension"] == dimension for node in nodes)


def test_build_site_copies_reviewed_translations(tmp_path):
    output = tmp_path / "dist"
    catalog = build_site(PROJECT_ROOT, output)

    assert (output / "index.html").is_file()
    assert (output / "assets" / "js" / "app.js").is_file()
    assert (output / "data" / "catalog.json").is_file()
    built = json.loads((output / "data" / "catalog.json").read_text(encoding="utf-8"))
    assert built["counts"] == catalog["counts"]
    for skill in catalog["skills"]:
        translation = skill.get("translation")
        if translation:
            assert (output / translation["path"]).is_file()


def test_build_refuses_project_root_as_output():
    try:
        build_site(PROJECT_ROOT, PROJECT_ROOT)
    except ValueError as exc:
        assert "项目根目录" in str(exc)
    else:
        raise AssertionError("expected output path guard")
