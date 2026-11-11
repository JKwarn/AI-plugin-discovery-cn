import json
import shutil

from scripts.validate.validate_taxonomy import Validator


def test_pstack_fixture_passes(data_dir, schemas_dir):
    validator = Validator(data_dir, schemas_dir)
    assert validator.run(), "\\n".join(validator.errors)


def test_rejects_cross_dimension_parent(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "scenarios.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["nodes"][1]["parent_id"] = "function.software_engineering"
    path.write_text(json.dumps(doc), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("belongs to functions" in error for error in validator.errors)


def test_rejects_tag_parent(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "tags.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["nodes"][0]["parent_id"] = "tag.architecture"
    path.write_text(json.dumps(doc), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("tags cannot have a parent" in error for error in validator.errors)


def test_rejects_parent_cycle(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "functions.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["nodes"][0]["parent_id"] = "function.codebase_analysis"
    path.write_text(json.dumps(doc), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("cycle detected" in error for error in validator.errors)
