#!/usr/bin/env python3
"""Validate Skill translation metadata, files, and upstream source freshness."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


class TranslationValidator:
    def __init__(self, data_dir: Path, schemas_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.project_root = self.data_dir.parent
        self.schemas_dir = schemas_dir.resolve()
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def read_json(self, path: Path) -> Any | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.errors.append(f"缺少必需文件：{path}")
        except (OSError, json.JSONDecodeError) as exc:
            self.errors.append(f"无法读取 {path}：{exc}")
        return None

    def run(self) -> bool:
        schema_path = self.schemas_dir / "translation-index.schema.json"
        schema = self.read_json(schema_path)
        registry_path = self.data_dir / "translations" / "skills.json"
        registry = self.read_json(registry_path)
        skill_index_path = self.data_dir / "skills" / "index.json"
        skill_index = self.read_json(skill_index_path)

        if not isinstance(schema, dict) or not isinstance(registry, dict):
            return False

        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        issues = sorted(validator.iter_errors(registry), key=lambda issue: list(issue.path))
        for issue in issues:
            location = ".".join(str(part) for part in issue.path) or "$"
            self.errors.append(f"{registry_path}:{location}: {issue.message}")
        if issues:
            return False

        if not isinstance(skill_index, dict) or not isinstance(skill_index.get("skills"), list):
            self.errors.append(f"{skill_index_path}：缺少 skills 数组")
            return False

        skills: dict[str, dict[str, Any]] = {}
        for skill in skill_index["skills"]:
            if not isinstance(skill, dict) or not isinstance(skill.get("id"), str):
                self.errors.append(f"{skill_index_path}：Skill 记录必须包含字符串 id")
                continue
            if skill["id"] in skills:
                self.errors.append(f"Skill 索引中存在重复 ID：{skill['id']}")
            skills[skill["id"]] = skill

        seen_locales: set[tuple[str, str]] = set()
        seen_paths: set[str] = set()
        for item in registry["translations"]:
            skill_id = item["skill_id"]
            locale_key = (skill_id, item["locale"])
            if locale_key in seen_locales:
                self.errors.append(f"重复的译文登记：{skill_id}/{item['locale']}")
            seen_locales.add(locale_key)

            path = item["path"]
            if path in seen_paths:
                self.errors.append(f"多个译文记录指向同一路径：{path}")
            seen_paths.add(path)

            relative = PurePosixPath(path)
            if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != path:
                self.errors.append(f"{skill_id}：译文路径不安全：{path}")
                continue
            if relative.parts[:2] != ("content", "skills"):
                self.errors.append(f"{skill_id}：译文必须位于 content/skills/ 下：{path}")
                continue
            target = self.project_root.joinpath(*relative.parts)
            if not target.is_file():
                self.errors.append(f"{skill_id}：找不到译文文件：{path}")

            source = skills.get(skill_id)
            if source is None:
                self.errors.append(f"译文引用了未知 Skill：{skill_id}")
                continue

            changed_fields = []
            for field in ("source_path", "source_file_hash", "source_blob_sha"):
                if item[field] != source.get(field):
                    changed_fields.append(field)
            if changed_fields:
                self.warnings.append(
                    f"{skill_id}/{item['locale']}：上游来源已变化（{', '.join(changed_fields)}），"
                    "当前译文应视为过期并重新审阅"
                )

        return not self.errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--schemas-dir", type=Path, default=Path("schemas"))
    args = parser.parse_args()

    validator = TranslationValidator(args.data_dir, args.schemas_dir)
    if not validator.run():
        for message in validator.errors:
            print(f"ERROR: {message}", file=sys.stderr)
        print(f"译文校验失败：{len(validator.errors)} 个错误", file=sys.stderr)
        return 1

    for message in validator.warnings:
        print(f"WARNING: {message}", file=sys.stderr)
    print(f"译文校验通过；过期译文：{len(validator.warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
