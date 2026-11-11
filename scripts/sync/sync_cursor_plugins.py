#!/usr/bin/env python3
"""Synchronize Cursor Plugins metadata from a checked-out upstream Git repository.

Only metadata and immutable source references are stored. Upstream Skill bodies
are not copied, translated, classified, or modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_ID = "cursor.plugins"
DEFAULT_REPOSITORY = "https://github.com/cursor/plugins"
MANIFEST_FORMATS = {".cursor-plugin": "cursor-plugin", ".claude-plugin": "claude-plugin"}


class SyncError(RuntimeError):
    pass


def run_git(source_dir: Path, *args: str, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(source_dir), *args],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise SyncError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def git_tree(source_dir: Path) -> dict[str, str]:
    raw = run_git(source_dir, "ls-tree", "-r", "--full-tree", "-z", "HEAD", binary=True)
    assert isinstance(raw, bytes)
    result: dict[str, str] = {}
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, object_type, blob_sha = metadata.decode("ascii").split()
        if object_type == "blob" and mode != "120000":
            result[raw_path.decode("utf-8")] = blob_sha
    return result


def git_blob(source_dir: Path, path: str) -> bytes:
    raw = run_git(source_dir, "show", f"HEAD:{path}", binary=True)
    assert isinstance(raw, bytes)
    return raw


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def slugify(value: str) -> str:
    original = value
    value = re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip(".-_")
    if not value:
        raise SyncError(f"Cannot create a stable identifier from: {original!r}")
    return value


def parse_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, str) else str(parsed)
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def parse_skill_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}
    fields: dict[str, str] = {}
    i = 1
    while i < end:
        match = re.match(r"^([A-Za-z0-9_-]+):(?:[ \t]*(.*))?$", lines[i])
        if not match:
            i += 1
            continue
        key, raw_value = match.group(1), (match.group(2) or "").strip()
        i += 1
        if raw_value in {">", ">-", "|", "|-"}:
            continuation: list[str] = []
            while i < end and (not lines[i].strip() or lines[i][:1].isspace()):
                if lines[i].strip():
                    continuation.append(lines[i].strip())
                i += 1
            fields[key] = ("\n" if raw_value.startswith("|") else " ").join(continuation).strip()
        else:
            fields[key] = parse_yaml_scalar(raw_value)
    return fields


def manifest_root_and_format(path: str) -> tuple[str, str] | None:
    parts = PurePosixPath(path).parts
    if not parts or parts[-1] != "plugin.json":
        return None
    if len(parts) >= 3 and parts[-2] in MANIFEST_FORMATS:
        return "/".join(parts[:-2]), MANIFEST_FORMATS[parts[-2]]
    if len(parts) >= 2:
        return "/".join(parts[:-1]), "agent-plugin"
    return None


def source_url(repository: str, revision: str, path: str) -> str:
    return f"{repository.rstrip('/')}/blob/{revision}/{path}"


def source_tree_url(repository: str, revision: str, path: str) -> str:
    return f"{repository.rstrip('/')}/tree/{revision}/{path}"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncError(f"Cannot read JSON file {path}: {exc}") from exc


def write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def all_records(document: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    records = document.get(key, [])
    if not isinstance(records, list):
        raise SyncError(f"Expected '{key}' to be an array")
    return {
        item["id"]: item for item in records
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def active_records(document: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {
        resource_id: item
        for resource_id, item in all_records(document, key).items()
        if item.get("status", "active") == "active"
    }


def build_current_resources(
    source_dir: Path, repository: str
) -> tuple[str, str, list[dict[str, Any]], list[dict[str, Any]]]:
    revision = str(run_git(source_dir, "rev-parse", "HEAD"))
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SyncError(f"Unexpected upstream revision: {revision}")
    commit_date = str(run_git(source_dir, "show", "-s", "--format=%cI", "HEAD"))
    tree = git_tree(source_dir)

    manifests_by_root: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(p for p in tree if p.endswith("/plugin.json")):
        root_and_format = manifest_root_and_format(path)
        if root_and_format is None:
            continue
        plugin_root, manifest_format = root_and_format
        raw = git_blob(source_dir, path)
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SyncError(f"Invalid manifest {path}: {exc}") from exc
        if not isinstance(manifest, dict) or not isinstance(manifest.get("name"), str):
            raise SyncError(f"Manifest must be an object with a string name: {path}")
        manifests_by_root.setdefault(plugin_root, []).append({
            "path": path, "format": manifest_format, "name": manifest["name"],
            "display_name": manifest.get("displayName"),
            "description": manifest.get("description"), "version": manifest.get("version"),
            "source_blob_sha": tree[path], "source_file_hash": sha256(raw),
            "source_revision": revision, "source_url": source_url(repository, revision, path),
        })

    if not manifests_by_root:
        raise SyncError("No supported plugin.json manifests were found in the source tree")

    plugin_roots = sorted(manifests_by_root, key=lambda value: (-len(value), value))
    plugins: list[dict[str, Any]] = []
    plugin_ids: set[str] = set()
    for root in sorted(manifests_by_root):
        plugin_id = ".".join(slugify(part) for part in PurePosixPath(root).parts)
        if plugin_id in plugin_ids:
            raise SyncError(f"Duplicate Plugin ID derived from source paths: {plugin_id}")
        plugin_ids.add(plugin_id)
        records = manifests_by_root[root]
        priority = {"cursor-plugin": 0, "agent-plugin": 1, "claude-plugin": 2}
        records.sort(key=lambda item: (priority.get(item["format"], 9), item["path"]))
        primary = records[0]
        plugins.append({
            "id": plugin_id, "name": primary["name"],
            "display_name": primary.get("display_name") or primary["name"],
            "description": primary.get("description") or "", "source_path": root,
            "source_url": source_tree_url(repository, revision, root),
            "source_revision": revision, "manifests": records, "status": "active",
        })

    skills: list[dict[str, Any]] = []
    skill_ids: set[str] = set()
    for path in sorted(tree):
        parts = PurePosixPath(path).parts
        if not path.endswith("/SKILL.md") or "skills" not in parts[1:-1]:
            continue
        matching_roots = [root for root in plugin_roots if path.startswith(root + "/")]
        if not matching_roots:
            raise SyncError(f"Skill has no matching Plugin manifest: {path}")
        plugin_root = matching_roots[0]
        plugin_id = ".".join(slugify(part) for part in PurePosixPath(plugin_root).parts)
        root_parts = PurePosixPath(plugin_root).parts
        skill_parts = parts[len(root_parts):]
        skills_index = skill_parts.index("skills")
        relative_skill_parts = skill_parts[skills_index + 1:-1]
        raw = git_blob(source_dir, path)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SyncError(f"Skill file is not valid UTF-8: {path}") from exc
        frontmatter = parse_skill_frontmatter(text)
        fallback_name = relative_skill_parts[-1] if relative_skill_parts else PurePosixPath(path).parent.name
        skill_name = frontmatter.get("name") or fallback_name
        path_identity = (
            ".".join(slugify(part) for part in relative_skill_parts)
            if relative_skill_parts else slugify(skill_name)
        )
        skill_id = f"{plugin_id}.{path_identity}"
        if skill_id in skill_ids:
            raise SyncError(f"Duplicate Skill ID derived from source paths: {skill_id}")
        skill_ids.add(skill_id)
        skills.append({
            "id": skill_id, "plugin_id": plugin_id, "name": skill_name,
            "description": frontmatter.get("description", ""), "source_path": path,
            "source_url": source_url(repository, revision, path),
            "source_revision": revision, "source_file_hash": sha256(raw),
            "source_blob_sha": tree[path], "status": "active",
        })
    return revision, commit_date, plugins, skills


def preserve_file_revisions(
    current: list[dict[str, Any]], previous: dict[str, dict[str, Any]],
    nested_key: str | None = None,
) -> None:
    for record in current:
        old = previous.get(record["id"])
        if old is None:
            continue
        if nested_key:
            old_nested = {
                item["path"]: item for item in old.get(nested_key, [])
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            }
            for nested in record.get(nested_key, []):
                prior = old_nested.get(nested["path"])
                if prior and prior.get("source_blob_sha") == nested.get("source_blob_sha"):
                    nested["source_revision"] = prior.get("source_revision", nested["source_revision"])
                    nested["source_url"] = prior.get("source_url", nested["source_url"])
            unchanged = (
                len(old_nested) == len(record.get(nested_key, []))
                and all(old_nested.get(item["path"], {}).get("source_blob_sha") == item["source_blob_sha"]
                        for item in record.get(nested_key, []))
            )
            if unchanged:
                record["source_revision"] = old.get("source_revision", record["source_revision"])
                record["source_url"] = old.get("source_url", record["source_url"])
        elif old.get("source_file_hash") == record.get("source_file_hash"):
            record["source_revision"] = old.get("source_revision", record["source_revision"])
            record["source_url"] = old.get("source_url", record["source_url"])


def add_removed_records(
    current: list[dict[str, Any]], previous: dict[str, dict[str, Any]], revision: str
) -> list[dict[str, Any]]:
    current_ids = {item["id"] for item in current}
    result = list(current)
    for resource_id, old in previous.items():
        if resource_id not in current_ids:
            removed = dict(old)
            if old.get("status", "active") != "removed":
                removed["status"] = "removed"
                removed["removed_in_revision"] = revision
            result.append(removed)
    return sorted(result, key=lambda item: item["id"])


def compare_resources(
    current: list[dict[str, Any]], previous: dict[str, dict[str, Any]], resource_type: str
) -> dict[str, list[str]]:
    now = {item["id"]: item for item in current}
    added, removed = sorted(set(now) - set(previous)), sorted(set(previous) - set(now))
    modified: list[str] = []
    for resource_id in sorted(set(now) & set(previous)):
        old, new = previous[resource_id], now[resource_id]
        if resource_type == "skills":
            changed = old.get("source_file_hash") != new.get("source_file_hash")
        else:
            old_blobs = {x.get("path"): x.get("source_blob_sha") for x in old.get("manifests", [])}
            new_blobs = {x.get("path"): x.get("source_blob_sha") for x in new.get("manifests", [])}
            changed = old_blobs != new_blobs
        if changed:
            modified.append(resource_id)
    return {"added": added, "removed": removed, "modified": modified}


def synchronize(
    source_dir: Path, data_dir: Path, repository: str = DEFAULT_REPOSITORY,
    dry_run: bool = False,
) -> dict[str, Any]:
    source_dir, data_dir = source_dir.resolve(), data_dir.resolve()
    if not (source_dir / ".git").exists():
        raise SyncError(f"Source directory is not a Git checkout: {source_dir}")
    revision, commit_date, current_plugins, current_skills = build_current_resources(source_dir, repository)

    source_index_path = data_dir / "sources" / "index.json"
    plugin_index_path = data_dir / "plugins" / "index.json"
    skill_index_path = data_dir / "skills" / "index.json"
    source_index = read_json(source_index_path, {"schema_version": "1.0.0", "sources": []})
    plugin_index = read_json(plugin_index_path, {"schema_version": "1.0.0", "plugins": []})
    skill_index = read_json(skill_index_path, {"schema_version": "1.0.0", "skills": []})
    previous_all_plugins = all_records(plugin_index, "plugins")
    previous_all_skills = all_records(skill_index, "skills")
    previous_plugins = {
        key: value for key, value in previous_all_plugins.items()
        if value.get("status", "active") == "active"
    }
    previous_skills = {
        key: value for key, value in previous_all_skills.items()
        if value.get("status", "active") == "active"
    }

    preserve_file_revisions(current_plugins, previous_plugins, nested_key="manifests")
    preserve_file_revisions(current_skills, previous_skills)
    changes = {
        "plugins": compare_resources(current_plugins, previous_plugins, "plugins"),
        "skills": compare_resources(current_skills, previous_skills, "skills"),
    }
    all_plugins = add_removed_records(current_plugins, previous_all_plugins, revision)
    all_skills = add_removed_records(current_skills, previous_all_skills, revision)

    source_records = source_index.get("sources", [])
    if not isinstance(source_records, list):
        raise SyncError("Source index field 'sources' must be an array")
    source_record = next((item for item in source_records if item.get("id") == SOURCE_ID), None)
    if source_record is None:
        source_record = {
            "id": SOURCE_ID, "name": "Cursor Plugins",
            "repository": repository, "access": "read_only",
        }
        source_records.append(source_record)
    source_record.update({
        "branch": "main", "latest_revision": revision, "latest_commit_date": commit_date,
        "latest_snapshot": f"sources/snapshots/{SOURCE_ID}/{revision}.json",
        "plugin_count": len(current_plugins), "skill_count": len(current_skills),
    })

    snapshot = {
        "schema_version": "1.0.0", "source_id": SOURCE_ID, "repository": repository,
        "branch": "main", "revision": revision, "commit_date": commit_date,
        "counts": {
            "plugins": len(current_plugins), "skills": len(current_skills),
            "manifests": sum(len(item["manifests"]) for item in current_plugins),
        },
        "changes": changes, "plugins": current_plugins, "skills": current_skills,
    }
    snapshot_path = data_dir / "sources" / "snapshots" / SOURCE_ID / f"{revision}.json"
    report = {
        "revision": revision, "commit_date": commit_date, "counts": snapshot["counts"],
        "changes": changes, "snapshot_path": str(snapshot_path), "dry_run": dry_run,
    }
    if dry_run:
        return report
    write_json(source_index_path, source_index)
    write_json(plugin_index_path, {"schema_version": "1.0.0", "plugins": all_plugins})
    write_json(skill_index_path, {"schema_version": "1.0.0", "skills": all_skills})
    if not snapshot_path.exists():
        write_json(snapshot_path, snapshot)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--repo-url", default=DEFAULT_REPOSITORY)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = synchronize(args.source_dir, args.data_dir, args.repo_url, args.dry_run)
    except SyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
