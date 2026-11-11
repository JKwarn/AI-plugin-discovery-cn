import json
import shutil

from scripts.validate.validate_taxonomy import Validator


def test_empty_changelog_is_valid(data_dir, schemas_dir):
    validator = Validator(data_dir, schemas_dir)
    assert validator.run(), "\n".join(validator.errors)


def test_rejects_duplicate_change_id(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "changelog.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    entry = {
        "change_id": "change.duplicate",
        "taxonomy_version": "1.0.1",
        "effective_at": "2026-11-11",
        "type": "add",
        "dimension": "functions",
        "category_ids": ["function.software_engineering"],
        "summary": "新增功能分类"
    }
    document["entries"] = [entry, dict(entry)]
    path.write_text(json.dumps(document), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("Duplicate changelog change_id" in error for error in validator.errors)


def test_rejects_unknown_category_reference(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "changelog.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entries"] = [{
        "change_id": "change.unknown_category",
        "taxonomy_version": "1.0.1",
        "effective_at": "2026-11-11",
        "type": "add",
        "dimension": "functions",
        "category_ids": ["function.does_not_exist"],
        "summary": "测试未知分类引用"
    }]
    path.write_text(json.dumps(document), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("unknown category 'function.does_not_exist'" in error for error in validator.errors)


def test_migration_change_requires_existing_migration(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    path = copied / "taxonomy" / "changelog.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entries"] = [{
        "change_id": "change.missing_migration",
        "taxonomy_version": "1.0.1",
        "effective_at": "2026-11-11",
        "type": "deprecate",
        "dimension": "functions",
        "category_ids": ["function.software_engineering"],
        "summary": "测试缺失迁移引用",
        "migration_id": "migration.does_not_exist"
    }]
    path.write_text(json.dumps(document), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("unknown migration 'migration.does_not_exist'" in error for error in validator.errors)


def test_migration_change_dimension_must_match(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    migration_path = copied / "taxonomy" / "migrations.json"
    migrations = json.loads(migration_path.read_text(encoding="utf-8"))
    migrations["migrations"] = [{
        "migration_id": "migration.test",
        "type": "deprecate",
        "dimension": "functions",
        "from_ids": ["function.software_engineering"],
        "to_ids": [],
        "effective_at": "2026-11-11",
        "reason": "测试迁移维度"
    }]
    migration_path.write_text(json.dumps(migrations), encoding="utf-8")

    changelog_path = copied / "taxonomy" / "changelog.json"
    changelog = json.loads(changelog_path.read_text(encoding="utf-8"))
    changelog["entries"] = [{
        "change_id": "change.dimension_mismatch",
        "taxonomy_version": "1.0.1",
        "effective_at": "2026-11-11",
        "type": "deprecate",
        "dimension": "roles",
        "category_ids": ["function.software_engineering"],
        "summary": "测试维度不匹配",
        "migration_id": "migration.test"
    }]
    changelog_path.write_text(json.dumps(changelog), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("migration dimension 'functions' does not match changelog dimension 'roles'" in error
               for error in validator.errors)

def test_migration_change_type_must_match(tmp_path, data_dir, schemas_dir):
    copied = tmp_path / "data"
    shutil.copytree(data_dir, copied)
    migration_path = copied / "taxonomy" / "migrations.json"
    migrations = json.loads(migration_path.read_text(encoding="utf-8"))
    migrations["migrations"] = [{
        "migration_id": "migration.test",
        "type": "deprecate",
        "dimension": "functions",
        "from_ids": ["function.software_engineering"],
        "to_ids": [],
        "effective_at": "2026-11-11",
        "reason": "测试迁移类型"
    }]
    migration_path.write_text(json.dumps(migrations), encoding="utf-8")

    changelog_path = copied / "taxonomy" / "changelog.json"
    changelog = json.loads(changelog_path.read_text(encoding="utf-8"))
    changelog["entries"] = [{
        "change_id": "change.type_mismatch",
        "taxonomy_version": "1.0.1",
        "effective_at": "2026-11-11",
        "type": "archive",
        "dimension": "functions",
        "category_ids": ["function.software_engineering"],
        "summary": "测试迁移类型不匹配",
        "migration_id": "migration.test"
    }]
    changelog_path.write_text(json.dumps(changelog), encoding="utf-8")

    validator = Validator(copied, schemas_dir)
    assert not validator.run()
    assert any("migration type 'deprecate' does not match changelog type 'archive'" in error
               for error in validator.errors)
