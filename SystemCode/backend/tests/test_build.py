from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from anchorai.scenario.build import build_tables, load_kaggle
from anchorai.scenario.tables import KAGGLE_COLUMNS, read_tables, write_tables

FIXTURES = Path(__file__).parent / "fixtures"


def _raw_csv(tmp_path: Path) -> Path:
    # Kaggle ships capitalised headers, e.g. Near_Location and Churn.
    members = pd.read_csv(FIXTURES / "members.csv")[list(KAGGLE_COLUMNS)]
    members.columns = [c.capitalize() if c != "gender" else c for c in members.columns]
    path = tmp_path / "gym_churn_us.csv"
    members.to_csv(path, index=False)
    return path


def test_build_writes_valid_tables_deterministically(tmp_path):
    raw = load_kaggle(_raw_csv(tmp_path))
    write_tables(build_tables(raw, seed=7), tmp_path / "a")
    write_tables(build_tables(raw, seed=7), tmp_path / "b")
    a, b = read_tables(tmp_path / "a"), read_tables(tmp_path / "b")
    for name in a:
        assert_frame_equal(a[name], b[name])
    members = a["members"]
    assert set(members.loc[members["split"] == "test", "churn"]) == {0, 1}
