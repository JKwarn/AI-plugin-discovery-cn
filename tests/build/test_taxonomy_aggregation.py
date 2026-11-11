import copy
import json
from pathlib import Path

from scripts.build.aggregate_taxonomy import aggregate_taxonomy


def make_approved(data_dir):
    assignment_path = data_dir / "assignments" / "skills.json"
    document = json.loads(assignment_path.read_text(encoding="utf-8"))
    for assignment in document["assignments"].values():
        for items in assignment["dimensions"].values():
            for item in items:
                item["status"] = "approved"
                item["reviewed_by"] = "test-reviewer"
                item["reviewed_at"] = "2026-11-11T00:00:00Z"
    assignment_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def copy_fixture(tmp_path):
    source = Path(__file__).resolve().parents[1] / "fixtures" / "pstack" / "data"
    target = tmp_path / "data"
    import shutil

    shutil.copytree(source, target)
    return target


def test_proposed_assignments_are_not_published(tmp_path):
    data_dir = copy_fixture(tmp_path)

    result = aggregate_taxonomy(data_dir)

    assert result["dimensions"]["functions"]["function.software_engineering"]["skill_ids"] == []
    assert result["plugins"] == {}


def test_parent_category_aggregates_descendant_skills(tmp_path):
    data_dir = copy_fixture(tmp_path)
    make_approved(data_dir)

    result = aggregate_taxonomy(data_dir)
    functions = result["dimensions"]["functions"]

    assert functions["function.software_engineering"] == {
        "direct_skill_ids": [],
        "descendant_skill_ids": [
            "pstack.architect",
            "pstack.how",
            "pstack.tdd",
        ],
        "skill_ids": [
            "pstack.architect",
            "pstack.how",
            "pstack.tdd",
        ],
    }
    assert functions["function.software_testing"]["skill_ids"] == ["pstack.tdd"]
    assert functions["function.codebase_analysis"]["direct_skill_ids"] == ["pstack.how"]


def test_plugin_aggregate_preserves_source_skill_ids_and_deduplicates(tmp_path):
    data_dir = copy_fixture(tmp_path)
    make_approved(data_dir)

    assignment_path = data_dir / "assignments" / "skills.json"
    document = json.loads(assignment_path.read_text(encoding="utf-8"))
    # One Skill may contribute through multiple children to the same ancestor.
    document["assignments"]["pstack.how"]["dimensions"]["functions"].append({
        "category_id": "function.software_design",
        "reason": "Additional fixture path for deduplication coverage.",
        "confidence": 0.5,
        "status": "approved",
        "reviewed_by": "test-reviewer",
        "reviewed_at": "2026-11-11T00:00:00Z",
    })
    assignment_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = aggregate_taxonomy(data_dir)
    plugin_functions = result["plugins"]["pstack"]["dimensions"]["functions"]

    assert plugin_functions["function.software_engineering"]["source_skill_ids"] == [
        "pstack.architect",
        "pstack.how",
        "pstack.tdd",
    ]
    assert plugin_functions["function.software_design"]["source_skill_ids"] == [
        "pstack.architect",
        "pstack.how",
    ]


def test_removed_skills_do_not_contribute(tmp_path):
    data_dir = copy_fixture(tmp_path)
    make_approved(data_dir)

    skill_path = data_dir / "skills" / "index.json"
    document = json.loads(skill_path.read_text(encoding="utf-8"))
    for skill in document["skills"]:
        if skill["id"] == "pstack.tdd":
            skill["status"] = "removed"
    skill_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = aggregate_taxonomy(data_dir)

    assert result["dimensions"]["functions"]["function.software_testing"]["skill_ids"] == []
