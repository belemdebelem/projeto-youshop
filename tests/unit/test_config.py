from youshop_finance.config import get_settings


def test_settings_defaults():
    s = get_settings()
    assert s.default_seed == 42
    assert s.amount_tolerance == 0.01
    assert s.duckdb_path.name.endswith(".duckdb")
