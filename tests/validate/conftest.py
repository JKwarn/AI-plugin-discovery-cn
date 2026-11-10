from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DATA = ROOT / "tests" / "fixtures" / "pstack" / "data"
SCHEMAS = ROOT / "schemas"

@pytest.fixture
def data_dir():
    return FIXTURE_DATA

@pytest.fixture
def schemas_dir():
    return SCHEMAS
