import json
import shutil

from scripts.validate.validate_taxonomy import Validator


def test_rejects_unknown_category(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "assignments" / "skills.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["assignments"]["pstack.how"]["dimensions"]["functions"][0]["category_id"] = "function.not_real"
    path.write_text(json.dumps(doc), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("unknown category" in error for error in validator.errors)


def test_strict_mode_requires_approved_function(data_dir, schemas_dir):
    validator = Validator(data_dir, schemas_dir, strict_approved=True)
    assert not validator.run()
    assert any("approved function assignment is required" in error for error in validator.errors)
