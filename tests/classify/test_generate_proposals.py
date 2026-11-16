import json
import shutil

from scripts.classify.generate_proposals import generate_proposals


def make_data(tmp_path, data_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
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

    assert "pstack.how" in by_skill
    how = by_skill["pstack.how"]["payload"]["dimensions"]
    assert any(item["category_id"] == "function.codebase_analysis"
               for item in how["functions"])
    assert all(item["evidence"] for values in how.values() for item in values)
    assert all(item["source_revision"] for values in how.values() for item in values)


def test_ignores_removed_skills_and_unknown_taxonomy_ids(tmp_path, data_dir):
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
