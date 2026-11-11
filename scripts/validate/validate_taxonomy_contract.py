#!/usr/bin/env python3
"""Validate taxonomy invariants that span multiple JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DIMENSIONS = ("functions", "roles", "scenarios", "tags")


def read_json(path: Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: cannot read JSON: {exc}")
        return None


def validate_taxonomy_contract(data_dir: Path) -> list[str]:
    data_dir = data_dir.resolve()
    errors: list[str] = []
    nodes: dict[str, str] = {}
    slugs: dict[tuple[str, str], str] = {}

    for dimension in DIMENSIONS:
        path = data_dir / "taxonomy" / f"{dimension}.json"
        document = read_json(path, errors)
        if not isinstance(document, dict):
            continue
        for node in document.get("nodes", []):
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            slug = node.get("slug")
            if isinstance(node_id, str):
                previous_dimension = nodes.get(node_id)
                if previous_dimension is not None:
                    errors.append(
                        f"{path}: duplicate taxonomy ID '{node_id}' "
                        f"(already declared in {previous_dimension})"
                    )
                else:
                    nodes[node_id] = dimension
            if isinstance(slug, str):
                key = (dimension, slug)
                previous_id = slugs.get(key)
                if previous_id is not None:
                    errors.append(
                        f"{path}: duplicate slug '{slug}' in {dimension} "
                        f"('{previous_id}' and '{node_id}')"
                    )
                else:
                    slugs[key] = str(node_id)

    migration_path = data_dir / "taxonomy" / "migrations.json"
    migration_document = read_json(migration_path, errors)
    if not isinstance(migration_document, dict):
        return errors

    seen_migration_ids: set[str] = set()
    for migration in migration_document.get("migrations", []):
        if not isinstance(migration, dict):
            continue
        migration_id = migration.get("migration_id", "<unknown>")
        if migration_id in seen_migration_ids:
            errors.append(f"{migration_id}: duplicate migration_id")
        seen_migration_ids.add(migration_id)

        kind = migration.get("type")
        dimension = migration.get("dimension")
        from_ids = migration.get("from_ids", [])
        to_ids = migration.get("to_ids", [])

        if kind == "merge" and (len(from_ids) < 2 or len(to_ids) != 1):
            errors.append(
                f"{migration_id}: merge needs >=2 from_ids and exactly 1 to_id"
            )
        elif kind == "split" and (len(from_ids) != 1 or len(to_ids) < 2):
            errors.append(
                f"{migration_id}: split needs exactly 1 from_id and >=2 to_ids"
            )
        elif kind in ("deprecate", "archive") and (
            len(from_ids) != 1 or len(to_ids) != 0
        ):
            errors.append(
                f"{migration_id}: {kind} needs exactly 1 from_id and no to_ids"
            )

        for field_name, category_ids in (("from_ids", from_ids), ("to_ids", to_ids)):
            for category_id in category_ids:
                actual_dimension = nodes.get(category_id)
                if actual_dimension is None:
                    errors.append(
                        f"{migration_id}: {field_name} references unknown "
                        f"category '{category_id}'"
                    )
                elif actual_dimension != dimension:
                    errors.append(
                        f"{migration_id}: {field_name} category '{category_id}' "
                        f"belongs to {actual_dimension}, not {dimension}"
                    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    errors = validate_taxonomy_contract(args.data_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Contract validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print("Taxonomy contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
