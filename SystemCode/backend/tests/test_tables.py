from pathlib import Path

import pytest

from anchorai.scenario.tables import SCHEMAS, SchemaError, check_integrity, read_tables

FIXTURES = Path(__file__).parent / "fixtures"


def test_fixture_matches_contract():
    tables = read_tables(FIXTURES)
    check_integrity(tables)
    for name, schema in SCHEMAS.items():
        assert {c: str(t) for c, t in tables[name].dtypes.items()} == schema


def test_integrity_rejects_dangling_foreign_key():
    tables = read_tables(FIXTURES)
    tables["attendance"].loc[0, "class_id"] = "K99"
    with pytest.raises(SchemaError, match="attendance.class_id"):
        check_integrity(tables)
