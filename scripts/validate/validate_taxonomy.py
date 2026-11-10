#!/usr/bin/env python3
"""Validate taxonomy data and cross-file references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

DIMENSIONS = {
    "functions": "function.",
    "roles": "role.",
    "scenarios": "scenario.",
    "tags": "tag.",
}
SCHEMA_FILES = {
    "taxonomy_node": "taxonomy-node.schema.json",
    "taxonomy_file": "taxonomy-file.schema.json",
    "assignment": "assignment.schema.json",
    "proposal": "proposal.schema.json",
    "migration": "migration.schema.json",
    "taxonomy_config": "taxonomy-config.schema.json",
}


class Validator:
    def __init__(self, data_dir: Path, schemas_dir: Path, strict_approved: bool = False,
                 strict_source: bool = False) -> None:
        self.data_dir = data_dir.resolve()
        self.schemas_dir = schemas_dir.resolve()
        self.strict_approved = strict_approved
        self.strict_source = strict_source
        self.errors: list[str] = []
        self.schemas: dict[str, dict[str, Any]] = {}
        self.nodes: dict[str, tuple[str, dict[str, Any]]] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def read_json(self, path: Path) -> Any | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.error(f"Missing required file: {path}")
        except (OSError, json.JSONDecodeError) as exc:
            self.error(f"Cannot read {path}: {exc}")
        return None

    def load_schemas(self) -> None:
        for key, filename in SCHEMA_FILES.items():
            schema = self.read_json(self.schemas_dir / filename)
            if isinstance(schema, dict):
                self.schemas[key] = schema
        for key in set(SCHEMA_FILES) - set(self.schemas):
            self.error(f"Required schema not loaded: {key}")

    def validate_document(self, document: Any, schema_key: str, label: str) -> bool:
        schema = self.schemas.get(schema_key)
        if schema is None:
            self.error(f"{label}: schema '{schema_key}' was not loaded")
            return False
        resolver = None
        if schema_key == "taxonomy_file":
            node_schema = self.schemas.get("taxonomy_node")
            if node_schema is None:
                self.error(f"{label}: taxonomy node schema was not loaded")
                return False
            resolver = RefResolver.from_schema(schema, store={node_schema["$id"]: node_schema})
        validator = Draft202012Validator(
            schema, resolver=resolver, format_checker=FormatChecker()
        )
        issues = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
        for issue in issues:
            location = ".".join(str(part) for part in issue.path) or "$"
            self.error(f"{label}:{location}: {issue.message}")
        return not issues

    def validate_taxonomy(self) -> None:
        for dimension, prefix in DIMENSIONS.items():
            path = self.data_dir / "taxonomy" / f"{dimension}.json"
            document = self.read_json(path)
            if document is None:
                continue
            self.validate_document(document, "taxonomy_file", str(path))
            if not isinstance(document, dict):
                continue
            if document.get("dimension") != dimension:
                self.error(f"{path}: dimension must be '{dimension}'")
            for node in document.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                node_id = node.get("id")
                if not isinstance(node_id, str):
                    continue
                if not node_id.startswith(prefix):
                    self.error(f"{path}: node '{node_id}' must use prefix '{prefix}'")
                if node_id in self.nodes:
                    self.error(f"Duplicate taxonomy ID: {node_id}")
                else:
                    self.nodes[node_id] = (dimension, node)

        for node_id, (dimension, node) in self.nodes.items():
            parent_id = node.get("parent_id")
            if dimension == "tags" and parent_id is not None:
                self.error(f"{node_id}: tags cannot have a parent")
            if parent_id is not None:
                parent = self.nodes.get(parent_id)
                if parent is None:
                    self.error(f"{node_id}: parent '{parent_id}' does not exist")
                elif parent[0] != dimension:
                    self.error(f"{node_id}: parent '{parent_id}' belongs to {parent[0]}")

        for node_id in self.nodes:
            visited: set[str] = set()
            current = node_id
            while current in self.nodes:
                if current in visited:
                    self.error(f"Taxonomy parent cycle detected from '{node_id}'")
                    break
                visited.add(current)
                parent_id = self.nodes[current][1].get("parent_id")
                if parent_id is None:
                    break
                current = parent_id

    def validate_source_metadata(self, resource: dict[str, Any], source: Path) -> None:
        revision = resource.get("source_revision")
        digest = resource.get("source_file_hash")
        resource_id = resource.get("id", "<unknown>")
        if self.strict_source and not revision:
            self.error(f"{source}: resource '{resource_id}' missing source_revision")
        if revision is not None and not re.fullmatch(r"[0-9a-f]{40}", str(revision)):
            self.error(f"{source}: resource '{resource_id}' has invalid source_revision")
        if self.strict_source and not digest:
            self.error(f"{source}: resource '{resource_id}' missing source_file_hash")
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            self.error(f"{source}: resource '{resource_id}' has invalid source_file_hash")

    def validate_assignments(self) -> None:
        path = self.data_dir / "assignments" / "skills.json"
        document = self.read_json(path)
        if document is None:
            return
        self.validate_document(document, "assignment", str(path))
        if not isinstance(document, dict):
            return

        skill_index_path = self.data_dir / "skills" / "index.json"
        skill_index = self.read_json(skill_index_path)
        skill_ids: set[str] = set()
        has_skill_index = isinstance(skill_index, dict) and isinstance(skill_index.get("skills"), list)
        if has_skill_index:
            for skill in skill_index["skills"]:
                if not isinstance(skill, dict) or not isinstance(skill.get("id"), str):
                    self.error(f"{skill_index_path}: every Skill must have a string id")
                    continue
                if skill["id"] in skill_ids:
                    self.error(f"Duplicate Skill ID: {skill['id']}")
                skill_ids.add(skill["id"])
                self.validate_source_metadata(skill, skill_index_path)

        assignments = document.get("assignments", {})
        for skill_id, assignment in assignments.items():
            if has_skill_index and skill_id not in skill_ids:
                self.error(f"Assignment references unknown Skill: {skill_id}")
            if not isinstance(assignment, dict):
                continue
            dimensions = assignment.get("dimensions", {})
            seen: set[tuple[str, str]] = set()
            approved_functions = 0
            for dimension in DIMENSIONS:
                for item in dimensions.get(dimension, []):
                    if not isinstance(item, dict):
                        continue
                    category_id = item.get("category_id")
                    key = (dimension, category_id)
                    if key in seen:
                        self.error(f"{skill_id}: duplicate {dimension} assignment '{category_id}'")
                    seen.add(key)
                    target = self.nodes.get(category_id)
                    if target is None:
                        self.error(f"{skill_id}: unknown category '{category_id}'")
                    elif target[0] != dimension:
                        self.error(f"{skill_id}: '{category_id}' is not in dimension '{dimension}'")
                    elif item.get("status") == "approved" and target[1].get("status") != "active":
                        self.error(f"{skill_id}: cannot approve non-active category '{category_id}'")
                    if item.get("status") == "approved":
                        if dimension == "functions":
                            approved_functions += 1
                        if not item.get("reviewed_by") or not item.get("reviewed_at"):
                            self.error(f"{skill_id}: approved assignment '{category_id}' needs reviewed_by and reviewed_at")
            if self.strict_approved and skill_id in skill_ids and approved_functions == 0:
                self.error(f"{skill_id}: at least one approved function assignment is required")

        if self.strict_approved and has_skill_index:
            for skill_id in sorted(skill_ids - set(assignments)):
                self.error(f"{skill_id}: missing assignment record")

    def validate_other_files(self) -> None:
        for filename, schema_key in (
            ("taxonomy-config.json", "taxonomy_config"),
            ("migrations.json", "migration"),
        ):
            path = self.data_dir / "taxonomy" / filename
            document = self.read_json(path)
            if document is not None:
                self.validate_document(document, schema_key, str(path))

        proposal_path = self.data_dir / "proposals" / "index.json"
        proposals = self.read_json(proposal_path)
        if proposals is not None:
            self.validate_document(proposals, "proposal", str(proposal_path))
        if isinstance(proposals, dict):
            for proposal in proposals.get("proposals", []):
                if proposal.get("status") == "approved":
                    self.error(f"{proposal_path}: approved proposal must be applied to formal data, not left in the proposal index")

        migration_path = self.data_dir / "taxonomy" / "migrations.json"
        migrations = self.read_json(migration_path)
        if isinstance(migrations, dict):
            for migration in migrations.get("migrations", []):
                kind = migration.get("type")
                from_ids = migration.get("from_ids", [])
                to_ids = migration.get("to_ids", [])
                migration_id = migration.get("migration_id", "<unknown>")
                if kind == "merge" and (len(from_ids) < 2 or len(to_ids) != 1):
                    self.error(f"{migration_id}: merge needs >=2 from_ids and exactly 1 to_id")
                if kind == "split" and (len(from_ids) != 1 or len(to_ids) < 2):
                    self.error(f"{migration_id}: split needs exactly 1 from_id and >=2 to_ids")
                for category_id in to_ids:
                    target = self.nodes.get(category_id)
                    if target is None:
                        self.error(f"{migration_id}: target '{category_id}' does not exist")
                    elif target[0] != migration.get("dimension"):
                        self.error(f"{migration_id}: target '{category_id}' has wrong dimension")

    def run(self) -> bool:
        self.load_schemas()
        self.validate_taxonomy()
        self.validate_assignments()
        self.validate_other_files()
        return not self.errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--schemas-dir", type=Path, default=Path("schemas"))
    parser.add_argument("--strict-approved", action="store_true",
                        help="require every indexed Skill to have an approved function category")
    parser.add_argument("--strict-source", action="store_true",
                        help="require source_revision and source_file_hash on indexed resources")
    args = parser.parse_args()

    validator = Validator(args.data_dir, args.schemas_dir, args.strict_approved, args.strict_source)
    if validator.run():
        print("Validation passed.")
        return 0
    for message in validator.errors:
        print(f"ERROR: {message}", file=sys.stderr)
    print(f"Validation failed with {len(validator.errors)} error(s).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
