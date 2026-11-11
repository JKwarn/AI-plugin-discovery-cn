#!/usr/bin/env python3
"""Build read-only taxonomy and Plugin aggregation views from approved assignments."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

DIMENSIONS = ("functions", "roles", "scenarios", "tags")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate_taxonomy(data_dir: Path) -> dict[str, Any]:
    """Return category and Plugin views without modifying source data.

    Only active Skills and approved assignments participate. Category ancestors
    collect descendant Skills; Plugin aggregates retain the IDs of the Skills
    that contributed each category. Sets ensure a Skill is counted only once
    per category, even when it reaches that category through multiple descendants.
    """
    taxonomy: dict[str, dict[str, dict[str, Any]]] = {}
    parent_by_id: dict[str, str | None] = {}

    for dimension in DIMENSIONS:
        document = read_json(data_dir / "taxonomy" / f"{dimension}.json")
        nodes = {
            node["id"]: node
            for node in document.get("nodes", [])
        }
        taxonomy[dimension] = nodes
        for node_id, node in nodes.items():
            parent_by_id[node_id] = node.get("parent_id")

    skill_document = read_json(data_dir / "skills" / "index.json")
    active_skills = {
        skill["id"]: skill
        for skill in skill_document.get("skills", [])
        if skill.get("status", "active") == "active"
    }
    assignment_document = read_json(data_dir / "assignments" / "skills.json")
    assignments = assignment_document.get("assignments", {})

    direct: dict[str, set[str]] = defaultdict(set)
    category_skills: dict[str, set[str]] = defaultdict(set)
    plugin_categories: dict[str, dict[str, dict[str, set[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set))
    )

    for skill_id, skill_assignment in assignments.items():
        skill = active_skills.get(skill_id)
        if skill is None:
            continue

        dimensions = skill_assignment.get("dimensions", {})
        for dimension in DIMENSIONS:
            for item in dimensions.get(dimension, []):
                if item.get("status") != "approved":
                    continue

                category_id = item.get("category_id")
                if category_id not in taxonomy[dimension]:
                    continue

                direct[category_id].add(skill_id)

                # A direct assignment contributes to its category and every
                # ancestor. The validator separately guarantees a valid tree.
                current: str | None = category_id
                visited: set[str] = set()
                while current is not None and current not in visited:
                    visited.add(current)
                    category_skills[current].add(skill_id)
                    plugin_categories[skill["plugin_id"]][dimension][current].add(
                        skill_id
                    )
                    current = parent_by_id.get(current)

    dimensions_result: dict[str, dict[str, dict[str, list[str]]]] = {}
    for dimension, nodes in taxonomy.items():
        dimension_result: dict[str, dict[str, list[str]]] = {}
        for category_id in nodes:
            direct_ids = direct[category_id]
            all_ids = category_skills[category_id]
            dimension_result[category_id] = {
                "direct_skill_ids": sorted(direct_ids),
                "descendant_skill_ids": sorted(all_ids - direct_ids),
                "skill_ids": sorted(all_ids),
            }
        dimensions_result[dimension] = dimension_result

    plugins_result: dict[str, dict[str, dict[str, dict[str, list[str]]]]] = {}
    for plugin_id, dimensions in plugin_categories.items():
        plugins_result[plugin_id] = {"dimensions": {}}
        for dimension, categories in dimensions.items():
            plugins_result[plugin_id]["dimensions"][dimension] = {
                category_id: {"source_skill_ids": sorted(skill_ids)}
                for category_id, skill_ids in sorted(categories.items())
            }

    return {
        "dimensions": dimensions_result,
        "plugins": plugins_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = aggregate_taxonomy(args.data_dir)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
