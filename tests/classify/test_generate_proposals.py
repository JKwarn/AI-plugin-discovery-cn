import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from scripts.classify.generate_proposals import generate_proposals


def make_data(tmp_path, data_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    skills_path = copied / "skills" / "index.json"
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
    descriptions = {
        "pstack.how": (
            "Explore a codebase to explain how an existing subsystem works. "
            "Analyze architecture and module responsibilities without modifying code."
        ),
        "pstack.architect": (
            "Software architect workflow for system design, architecture decisions, "
            "and changes across module boundaries."
        ),
        "pstack.tdd": (
            "Use test-driven development (TDD): write a failing test before fixing a bug "
            "and add a regression test."
        ),
    }
    for skill in skills["skills"]:
        skill["name"] = skill["id"].split(".")[-1]
        skill["description"] = descriptions.get(skill["id"], "")
    skills_path.write_text(json.dumps(skills), encoding="utf-8")
    return copied


def test_generates_only_pending_proposals_for_active_skills(tmp_path, data_dir):
    copied = make_data(tmp_path, data_dir)
    proposals = generate_proposals(copied)

    assert proposals
    assert all(item["kind"] == "assignment" for item in proposals)
    assert all(item["status"] == "pending" for item in proposals)
    assert all(item["proposal_id"].startswith("proposal.assignment.") for item in proposals)
    assert all(item["payload"]["dimensions"] for item in proposals)
    assert all(
        assignment["status"] == "proposed"
        for proposal in proposals
        for assignments in proposal["payload"]["dimensions"].values()
        for assignment in assignments
    )


def test_pstack_candidates_have_traceable_evidence(tmp_path, data_dir):
    copied = make_data(tmp_path, data_dir)
    proposals = generate_proposals(copied)
    by_skill = {item["payload"]["skill_id"]: item for item in proposals}

    assert {"pstack.how", "pstack.architect", "pstack.tdd"} <= set(by_skill)
    how = by_skill["pstack.how"]["payload"]["dimensions"]
    assert any(item["category_id"] == "function.codebase_analysis"
               for item in how["functions"])
    assert all(item["evidence"] for values in how.values() for item in values)
    assert all(item["source_revision"] for values in how.values() for item in values)


def test_output_conforms_to_proposal_schema(tmp_path, data_dir):
    copied = make_data(tmp_path, data_dir)
    proposals = generate_proposals(copied)
    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "proposal.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    document = {"schema_version": "1.0.0", "proposals": proposals}

    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document))
    assert not errors, [error.message for error in errors]


def test_ignores_removed_skills(tmp_path, data_dir):
    copied = make_data(tmp_path, data_dir)
    skills_path = copied / "skills" / "index.json"
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
    skills["skills"] = [dict(skills["skills"][0], status="removed")]
    skills_path.write_text(json.dumps(skills), encoding="utf-8")

    proposals = generate_proposals(copied)
    assert proposals == []


def test_generator_does_not_modify_assignment_registry(tmp_path, data_dir):
    copied = make_data(tmp_path, data_dir)
    assignments_path = copied / "assignments" / "skills.json"
    before = assignments_path.read_bytes()

    generate_proposals(copied)

    assert assignments_path.read_bytes() == before
