import json
import shutil

from scripts.validate.validate_taxonomy_contract import validate_taxonomy_contract


def test_pstack_fixture_satisfies_cross_file_contract(data_dir):
    assert validate_taxonomy_contract(data_dir) == []


def test_rejects_duplicate_slug_within_dimension(tmp_path, data_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "functions.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["nodes"][1]["slug"] = document["nodes"][0]["slug"]
    path.write_text(json.dumps(document), encoding="utf-8")

    errors = validate_taxonomy_contract(copied)
    assert any("duplicate slug" in error for error in errors)


def test_rejects_unknown_migration_source(tmp_path, data_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "migrations.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["migrations"] = [
        {
            "migration_id": "migration.invalid_source",
            "type": "deprecate",
            "dimension": "functions",
            "from_ids": ["function.does_not_exist"],
            "to_ids": [],
            "effective_at": "2026-11-11",
            "reason": "Test invalid source reference"
        }
    ]
    path.write_text(json.dumps(document), encoding="utf-8")

    errors = validate_taxonomy_contract(copied)
    assert any("unknown category 'function.does_not_exist'" in error for error in errors)


def test_rejects_migration_dimension_mismatch(tmp_path, data_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "migrations.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["migrations"] = [
        {
            "migration_id": "migration.wrong_dimension",
            "type": "deprecate",
            "dimension": "roles",
            "from_ids": ["function.software_engineering"],
            "to_ids": [],
            "effective_at": "2026-11-11",
            "reason": "Test dimension mismatch"
        }
    ]
    path.write_text(json.dumps(document), encoding="utf-8")

    errors = validate_taxonomy_contract(copied)
    assert any("belongs to functions, not roles" in error for error in errors)


def test_rejects_duplicate_migration_id(tmp_path, data_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "migrations.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    entry = {
        "migration_id": "migration.duplicate",
        "type": "deprecate",
        "dimension": "functions",
        "from_ids": ["function.software_engineering"],
        "to_ids": [],
        "effective_at": "2026-11-11",
        "reason": "Test duplicate ID"
    }
    document["migrations"] = [entry, dict(entry)]
    path.write_text(json.dumps(document), encoding="utf-8")

    errors = validate_taxonomy_contract(copied)
    assert any("duplicate migration_id" in error for error in errors)
