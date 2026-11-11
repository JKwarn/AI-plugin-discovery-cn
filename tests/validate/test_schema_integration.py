import json

from jsonschema import Draft202012Validator

from scripts.validate.validate_taxonomy import SCHEMA_FILES


def test_all_schemas_are_valid():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    for filename in SCHEMA_FILES.values():
        schema = json.loads((root / "schemas" / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_all_fixture_taxonomy_files_match_schema(data_dir, schemas_dir):
    from jsonschema import FormatChecker, RefResolver, Draft202012Validator
    node_schema = json.loads((schemas_dir / "taxonomy-node.schema.json").read_text(encoding="utf-8"))
    schema = json.loads((schemas_dir / "taxonomy-file.schema.json").read_text(encoding="utf-8"))
    resolver = RefResolver.from_schema(schema, store={node_schema["$id"]: node_schema})
    validator = Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())
    for dimension in ("functions", "roles", "scenarios", "tags"):
        document = json.loads((data_dir / "taxonomy" / f"{dimension}.json").read_text(encoding="utf-8"))
        assert not list(validator.iter_errors(document))
