#!/usr/bin/env python3
"""Build the static GitHub Pages site from the repository's source data."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.build.aggregate_taxonomy import aggregate_taxonomy

DIMENSIONS = ("functions", "roles", "scenarios", "tags")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象: {path}")
    return value


def build_catalog(project_root: Path) -> dict[str, Any]:
    data_dir = project_root / "data"
    plugins = read_json(data_dir / "plugins" / "index.json").get("plugins", [])
    skills = read_json(data_dir / "skills" / "index.json").get("skills", [])
    assignments = read_json(data_dir / "assignments" / "skills.json").get("assignments", {})
    translations = read_json(data_dir / "translations" / "skills.json").get("translations", [])

    translation_by_skill: dict[str, dict[str, Any]] = {}
    for item in translations:
        if item.get("locale") == "zh-CN" and item.get("status") == "reviewed":
            translation_by_skill[item["skill_id"]] = item

    taxonomy: dict[str, list[dict[str, Any]]] = {}
    for dimension in DIMENSIONS:
        taxonomy[dimension] = [
            {**node, "dimension": dimension}
            for node in read_json(
                data_dir / "taxonomy" / f"{dimension}.json"
            ).get("nodes", [])
        ]

    aggregation = aggregate_taxonomy(data_dir)
    approved_by_skill: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for skill_id, record in assignments.items():
        dimensions: dict[str, list[dict[str, Any]]] = {}
        for dimension in DIMENSIONS:
            approved = [
                item for item in record.get("dimensions", {}).get(dimension, [])
                if item.get("status") == "approved"
            ]
            if approved:
                dimensions[dimension] = approved
        if dimensions:
            approved_by_skill[skill_id] = dimensions

    plugin_ids = {item.get("id") for item in plugins}
    normalized_skills = []
    for skill in skills:
        if skill.get("status", "active") != "active":
            continue
        plugin_id = skill.get("plugin_id")
        if plugin_id not in plugin_ids:
            continue
        normalized_skills.append({
            **skill,
            "approved_categories": approved_by_skill.get(skill["id"], {}),
            "translation": translation_by_skill.get(skill["id"]),
        })

    return {
        "schema_version": "1.0.0",
        "source": {
            "repository": "https://github.com/cursor/plugins",
            "revision": (
                normalized_skills[0].get("source_revision")
                if normalized_skills else None
            ),
        },
        "counts": {
            "plugins": sum(1 for item in plugins if item.get("status", "active") == "active"),
            "skills": len(normalized_skills),
            "reviewed_translations": len(translation_by_skill),
        },
        "plugins": [item for item in plugins if item.get("status", "active") == "active"],
        "skills": normalized_skills,
        "taxonomy": taxonomy,
        "aggregation": aggregation,
    }


def build_site(project_root: Path, output_dir: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    output_dir = output_dir.resolve()
    if output_dir == project_root or project_root in output_dir.parents:
        if output_dir == project_root:
            raise ValueError("输出目录不能是项目根目录")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for relative in ("index.html", "assets"):
        source = project_root / relative
        if source.is_dir():
            shutil.copytree(source, output_dir / relative)
        elif source.is_file():
            shutil.copy2(source, output_dir / relative)
        else:
            raise ValueError(f"缺少网站入口文件：{source}")

    catalog = build_catalog(project_root)
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for skill in catalog["skills"]:
        translation = skill.get("translation")
        if not translation:
            continue
        relative = Path(translation["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"不安全的译文路径：{relative}")
        source = project_root / relative
        if not source.is_file():
            raise ValueError(f"找不到已审核译文：{source}")
        destination = output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    catalog = build_site(args.project_root, args.output_dir)
    print(
        "网站构建完成："
        f"{catalog['counts']['plugins']} 个 Plugin，"
        f"{catalog['counts']['skills']} 个 Skill，"
        f"{catalog['counts']['reviewed_translations']} 份已审核译文"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
