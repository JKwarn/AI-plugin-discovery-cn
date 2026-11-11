import json
import shutil

from scripts.validate.validate_translations import TranslationValidator


def make_project(tmp_path, data_dir):
    root = tmp_path / "project"
    shutil.copytree(data_dir, root / "data")
    return root, root / "data"


def write_registry(data_dir, translations):
    path = data_dir / "translations" / "skills.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": "1.0.0",
        "translations": translations
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def sample_translation():
    return {
        "skill_id": "pstack.how",
        "locale": "zh-CN",
        "path": "content/skills/pstack.how/SKILL.zh-CN.md",
        "source_id": "cursor.plugins",
        "source_path": "pstack/skills/how/SKILL.md",
        "source_url": "https://github.com/cursor/plugins/blob/5866df557357d005b3c0c9d3da0d9e739b4bdde3/pstack/skills/how/SKILL.md",
        "source_revision": "5866df557357d005b3c0c9d3da0d9e739b4bdde3",
        "source_file_hash": "08a00079bb15b4258874ac3ff62d4ca7e94350ffedb521d0fd296dc9dd21904e",
        "source_blob_sha": "67edc340d4d8a9c7ab0b9e08c663e0e63b8d9125",
        "status": "draft",
        "translated_at": "2026-11-11T12:00:00Z"
    }


def test_empty_translation_registry_is_valid(data_dir, schemas_dir):
    validator = TranslationValidator(data_dir, schemas_dir)
    assert validator.run(), "\n".join(validator.errors)


def test_valid_translation_tracks_source_and_file(tmp_path, data_dir, schemas_dir):
    root, copied_data = make_project(tmp_path, data_dir)
    translation = sample_translation()
    target = root / translation["path"]
    target.parent.mkdir(parents=True)
    target.write_text("# 如何理解代码库\n", encoding="utf-8")
    write_registry(copied_data, [translation])

    validator = TranslationValidator(copied_data, schemas_dir)
    assert validator.run(), "\n".join(validator.errors)
    assert not validator.warnings


def test_rejects_unknown_skill(tmp_path, data_dir, schemas_dir):
    _, copied_data = make_project(tmp_path, data_dir)
    translation = sample_translation()
    translation["skill_id"] = "pstack.unknown"
    write_registry(copied_data, [translation])

    validator = TranslationValidator(copied_data, schemas_dir)
    assert not validator.run()
    assert any("未知 Skill" in error for error in validator.errors)


def test_rejects_missing_translation_file(tmp_path, data_dir, schemas_dir):
    _, copied_data = make_project(tmp_path, data_dir)
    write_registry(copied_data, [sample_translation()])

    validator = TranslationValidator(copied_data, schemas_dir)
    assert not validator.run()
    assert any("找不到译文文件" in error for error in validator.errors)


def test_rejects_duplicate_skill_locale(tmp_path, data_dir, schemas_dir):
    _, copied_data = make_project(tmp_path, data_dir)
    translation = sample_translation()
    write_registry(copied_data, [translation, dict(translation)])

    validator = TranslationValidator(copied_data, schemas_dir)
    assert not validator.run()
    assert any("重复的译文登记" in error for error in validator.errors)


def test_rejects_reviewed_translation_without_review_timestamp(tmp_path, data_dir, schemas_dir):
    _, copied_data = make_project(tmp_path, data_dir)
    translation = sample_translation()
    translation["status"] = "reviewed"
    write_registry(copied_data, [translation])

    validator = TranslationValidator(copied_data, schemas_dir)
    assert not validator.run()
    assert any("reviewed_at" in error for error in validator.errors)


def test_source_change_marks_translation_stale_without_failing(tmp_path, data_dir, schemas_dir):
    root, copied_data = make_project(tmp_path, data_dir)
    translation = sample_translation()
    target = root / translation["path"]
    target.parent.mkdir(parents=True)
    target.write_text("# 旧版译文\n", encoding="utf-8")
    skills_path = copied_data / "skills" / "index.json"
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
    skills["skills"][0]["source_file_hash"] = "f" * 64
    skills_path.write_text(json.dumps(skills), encoding="utf-8")
    write_registry(copied_data, [translation])

    validator = TranslationValidator(copied_data, schemas_dir)
    assert validator.run(), "\n".join(validator.errors)
    assert any("应视为过期" in warning for warning in validator.warnings)
