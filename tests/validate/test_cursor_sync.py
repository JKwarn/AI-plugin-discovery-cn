import json
import subprocess
from pathlib import Path

from scripts.sync.sync_cursor_plugins import synchronize


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return result.stdout.strip()


def commit_all(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)


def write(repo: Path, path: str, content: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def make_source_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "cursor-plugins"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    write(repo, "demo/.cursor-plugin/plugin.json", json.dumps({
        "name": "demo", "displayName": "Demo Plugin", "version": "1.0.0",
        "description": "Demo description", "skills": "./skills/"
    }))
    write(repo, "demo/plugin.json", json.dumps({
        "name": "demo-agent", "version": "1.0.0", "description": "Agent format"
    }))
    write(repo, "demo/skills/alpha/SKILL.md",
          "---\nname: alpha\ndescription: >-\n  Alpha skill description\n  continued on another line\n---\n\n# Alpha\n")
    write(repo, "demo/skills/obsolete/SKILL.md",
          "---\nname: obsolete\ndescription: Old skill\n---\n\n# Old\n")
    write(repo, "third_party/sample/.claude-plugin/plugin.json", json.dumps({
        "name": "sample", "version": "2.0.0", "description": "Nested third party plugin"
    }))
    write(repo, "third_party/sample/skills/check/SKILL.md",
          "---\nname: check\ndescription: Check things\n---\n\n# Check\n")
    commit_all(repo, "initial fixture")
    return repo


def test_sync_discovers_plugins_skills_and_manifest_formats(tmp_path: Path):
    source, data = make_source_repo(tmp_path), tmp_path / "data"
    report = synchronize(source, data)
    assert report["counts"] == {"plugins": 2, "skills": 3, "manifests": 3}
    assert len(report["changes"]["plugins"]["added"]) == 2
    assert len(report["changes"]["skills"]["added"]) == 3
    plugins = json.loads((data / "plugins" / "index.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in plugins["plugins"]}
    assert by_id["demo"]["display_name"] == "Demo Plugin"
    assert "/tree/" in by_id["demo"]["source_url"]
    assert {x["format"] for x in by_id["demo"]["manifests"]} == {"cursor-plugin", "agent-plugin"}
    assert by_id["third_party.sample"]["manifests"][0]["format"] == "claude-plugin"
    skills = json.loads((data / "skills" / "index.json").read_text(encoding="utf-8"))
    skill_by_id = {item["id"]: item for item in skills["skills"]}
    assert skill_by_id["demo.alpha"]["description"] == "Alpha skill description continued on another line"
    assert skill_by_id["third_party.sample.check"]["plugin_id"] == "third_party.sample"
    assert len(skill_by_id["demo.alpha"]["source_file_hash"]) == 64
    assert len(list((data / "sources" / "snapshots" / "cursor.plugins").glob("*.json"))) == 1


def test_sync_is_idempotent_and_preserves_original_file_revision(tmp_path: Path):
    source, data = make_source_repo(tmp_path), tmp_path / "data"
    first = synchronize(source, data)
    first_skills = json.loads((data / "skills" / "index.json").read_text(encoding="utf-8"))
    original = {x["id"]: x["source_revision"] for x in first_skills["skills"]}
    second = synchronize(source, data)
    second_skills = json.loads((data / "skills" / "index.json").read_text(encoding="utf-8"))
    assert second["changes"]["skills"] == {"added": [], "removed": [], "modified": []}
    assert {x["id"]: x["source_revision"] for x in second_skills["skills"]} == original
    assert first["revision"] == second["revision"]
    assert len(list((data / "sources" / "snapshots" / "cursor.plugins").glob("*.json"))) == 1


def test_sync_records_changes_and_keeps_removed_resources_as_tombstones(tmp_path: Path):
    source, data = make_source_repo(tmp_path), tmp_path / "data"
    synchronize(source, data)
    write(source, "demo/skills/alpha/SKILL.md",
          "---\nname: alpha\ndescription: Updated description\n---\n\n# Alpha updated\n")
    (source / "demo" / "skills" / "obsolete" / "SKILL.md").unlink()
    write(source, "demo/skills/new-skill/SKILL.md",
          "---\nname: new-skill\ndescription: New skill\n---\n\n# New\n")
    write(source, "demo/.cursor-plugin/plugin.json", json.dumps({
        "name": "demo", "displayName": "Demo Plugin", "version": "1.1.0",
        "description": "Demo description", "skills": "./skills/"
    }))
    commit_all(source, "update fixture")
    report = synchronize(source, data)
    assert report["changes"]["skills"]["added"] == ["demo.new-skill"]
    assert report["changes"]["skills"]["removed"] == ["demo.obsolete"]
    assert report["changes"]["skills"]["modified"] == ["demo.alpha"]
    assert report["changes"]["plugins"]["modified"] == ["demo"]
    index = json.loads((data / "skills" / "index.json").read_text(encoding="utf-8"))
    by_id = {x["id"]: x for x in index["skills"]}
    assert by_id["demo.obsolete"]["status"] == "removed"
    assert by_id["demo.obsolete"]["removed_in_revision"] == report["revision"]
    assert by_id["demo.alpha"]["source_revision"] == report["revision"]
    assert by_id["demo.new-skill"]["status"] == "active"
    assert len(list((data / "sources" / "snapshots" / "cursor.plugins").glob("*.json"))) == 2

    # A subsequent sync must retain tombstones instead of dropping old records.
    synchronize(source, data)
    index_after_repeat = json.loads(
        (data / "skills" / "index.json").read_text(encoding="utf-8")
    )
    by_id_after_repeat = {x["id"]: x for x in index_after_repeat["skills"]}
    assert by_id_after_repeat["demo.obsolete"]["status"] == "removed"
    assert by_id_after_repeat["demo.obsolete"]["removed_in_revision"] == report["revision"]
