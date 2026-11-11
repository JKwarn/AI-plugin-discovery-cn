import json
import re
from pathlib import Path


def test_pstack_fixture_is_pinned_to_one_upstream_revision():
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests" / "fixtures" / "pstack"
    snapshot = json.loads((fixture / "source-snapshot.json").read_text(encoding="utf-8"))
    skills_index = json.loads(
        (fixture / "data" / "skills" / "index.json").read_text(encoding="utf-8")
    )
    plugins_index = json.loads(
        (fixture / "data" / "plugins" / "index.json").read_text(encoding="utf-8")
    )

    revision = snapshot["revision"]
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    assert snapshot["repository"] == "https://github.com/cursor/plugins"
    assert snapshot["source_id"] == "cursor.plugins"

    snapshot_skills = {item["id"]: item for item in snapshot["skills"]}
    indexed_skills = {item["id"]: item for item in skills_index["skills"]}
    assert set(snapshot_skills) == {"pstack.how", "pstack.architect", "pstack.tdd"}
    assert set(indexed_skills) == set(snapshot_skills)

    for skill_id, item in snapshot_skills.items():
        assert indexed_skills[skill_id] == item
        assert item["source_revision"] == revision
        assert revision in item["source_url"]
        assert re.fullmatch(r"[0-9a-f]{64}", item["source_file_hash"])
        assert re.fullmatch(r"[0-9a-f]{40}", item["source_blob_sha"])

    plugins = plugins_index["plugins"]
    assert len(plugins) == 1
    assert plugins[0]["id"] == "pstack"
    assert plugins[0]["source_revision"] == revision

    manifests = plugins[0]["manifests"]
    assert {item["format"] for item in manifests} == {"agent-plugin", "cursor-plugin"}
    assert {item["path"] for item in manifests} == {
        "pstack/plugin.json",
        "pstack/.cursor-plugin/plugin.json",
    }
    assert all(re.fullmatch(r"[0-9a-f]{40}", item["source_blob_sha"]) for item in manifests)
