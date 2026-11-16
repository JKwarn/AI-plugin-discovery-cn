#!/usr/bin/env python3
"""Generate explainable, review-only taxonomy assignment proposals.

This is a deterministic baseline classifier, not an LLM classifier. It never
writes to the approved assignment registry or the formal taxonomy.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CLASSIFIER_VERSION = "rules-0.1.0"
DIMENSIONS = ("functions", "roles", "scenarios", "tags")

# Rules deliberately use high-signal phrases. Broad words such as "AI",
# "agent", "code", or "test" are not sufficient evidence on their own.
RULES: dict[str, dict[str, tuple[tuple[str, ...], float]]] = {
    "functions": {
        "function.codebase_analysis": (
            (r"codebase", r"code base", r"existing (?:code|sub)?system", r"repository analysis",
             r"understand.{0,30}(?:code|repository|subsystem)", r"explore.{0,20}code"),
            0.86,
        ),
        "function.software_design": (
            (r"software architect", r"system design", r"architecture design",
             r"design.{0,30}(?:module|system|architecture)", r"architect(?:ure)?(?:al)?"),
            0.82,
        ),
        "function.software_testing": (
            (r"regression test", r"test suite", r"unit test", r"integration test",
             r"run tests", r"test(?:ing)? strategy", r"compiler errors", r"type-check"),
            0.84,
        ),
        "function.test_driven_development": (
            (r"test-driven development", r"\bTDD\b", r"test first", r"failing test before",
             r"red[- ]green[- ]refactor"),
            0.91,
        ),
    },
    "roles": {
        "role.software_developer": (
            (r"software developer", r"software engineer", r"programmer",
             r"coding workflow", r"code review", r"write code"),
            0.80,
        ),
        "role.software_architect": (
            (r"software architect", r"system architect", r"architecture decision",
             r"architectural design", r"module boundary"),
            0.86,
        ),
    },
    "scenarios": {
        "scenario.understand_existing_subsystem": (
            (r"understand.{0,30}(?:existing )?(?:subsystem|codebase|repository)",
             r"how.{0,15}(?:the )?(?:system|codebase|subsystem) works",
             r"explore.{0,20}(?:existing )?(?:code|system)"),
            0.88,
        ),
        "scenario.design_cross_boundary_change": (
            (r"cross[- ](?:module|boundary)", r"module boundary",
             r"change.{0,20}(?:multiple|several) modules", r"system design"),
            0.84,
        ),
        "scenario.fix_bug_with_regression_test": (
            (r"fix(?:ing)? bugs?.{0,50}regression test",
             r"bug fix.{0,50}test", r"regression test.{0,50}bug",
             r"reproduce.{0,30}bug"),
            0.87,
        ),
    },
    "tags": {
        "tag.read_only": (
            (r"read-only", r"readonly", r"without modifying (?:the )?(?:code|repository)",
             r"analyze.{0,30}without changing"),
            0.82,
        ),
        "tag.architecture": (
            (r"architecture", r"architectural", r"module boundaries", r"system design"),
            0.78,
        ),
        "tag.test_driven": (
            (r"test-driven", r"\bTDD\b", r"failing test before", r"red[- ]green[- ]refactor"),
            0.90,
        ),
    },
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON 文件 {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象: {path}")
    return value


def collect_category_ids(data_dir: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for dimension in DIMENSIONS:
        document = read_json(data_dir / "taxonomy" / f"{dimension}.json")
        result[dimension] = {
            node["id"]
            for node in document.get("nodes", [])
            if isinstance(node, dict) and node.get("status") == "active"
        }
    return result


def find_evidence(text: str, patterns: tuple[str, ...]) -> list[str]:
    evidence: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            phrase = match.group(0).strip()
            if phrase and phrase.lower() not in {item.lower() for item in evidence}:
                evidence.append(phrase)
        if len(evidence) == 3:
            break
    return evidence


def generate_proposals(data_dir: Path) -> list[dict[str, Any]]:
    skill_doc = read_json(data_dir / "skills" / "index.json")
    category_ids = collect_category_ids(data_dir)
    source_doc = read_json(data_dir / "sources" / "index.json")
    sources = {
        item.get("id"): item
        for item in source_doc.get("sources", [])
        if isinstance(item, dict)
    }

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    proposals: list[dict[str, Any]] = []

    for skill in skill_doc.get("skills", []):
        if not isinstance(skill, dict) or skill.get("status", "active") != "active":
            continue
        skill_id = skill.get("id")
        if not isinstance(skill_id, str):
            continue

        searchable = " ".join(
            str(skill.get(field, "")) for field in ("name", "description", "source_path")
        )
        dimensions: dict[str, list[dict[str, Any]]] = {}

        for dimension, rules in RULES.items():
            matches: list[dict[str, Any]] = []
            for category_id, (patterns, confidence) in rules.items():
                if category_id not in category_ids.get(dimension, set()):
                    continue
                evidence = find_evidence(searchable, patterns)
                if not evidence:
                    continue
                matches.append({
                    "category_id": category_id,
                    "reason": (
                        "资源元数据中出现了与该分类规则直接相关的表述："
                        + "、".join(f"“{item}”" for item in evidence)
                        + "。该结果仅为规则匹配候选，需人工核对 Skill 原文后决定是否批准。"
                    ),
                    "confidence": confidence,
                    "status": "proposed",
                    "source_revision": skill.get("source_revision"),
                    "classifier_version": CLASSIFIER_VERSION,
                    "evidence": evidence,
                })
            if matches:
                dimensions[dimension] = matches

        if not dimensions:
            continue

        source = sources.get("cursor.plugins", {})
        revision = skill.get("source_revision") or source.get("latest_revision")
        proposal_id = f"proposal.assignment.{skill_id}"
        proposals.append({
            "proposal_id": proposal_id,
            "kind": "assignment",
            "status": "pending",
            "created_at": created_at,
            "description": f"为 Skill「{skill_id}」生成基于元数据证据的分类候选；不代表审核通过。",
            "source_revision": revision,
            "payload": {
                "skill_id": skill_id,
                "dimensions": dimensions,
                "classifier": CLASSIFIER_VERSION,
            },
        })

    return proposals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path,
        help="将候选提案写入指定文件；省略时输出 JSON 到标准输出",
    )
    args = parser.parse_args()

    try:
        proposals = generate_proposals(args.data_dir)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    document = {"schema_version": "1.0.0", "proposals": proposals}
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"已生成 {len(proposals)} 条待审核提案：{args.output}")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
