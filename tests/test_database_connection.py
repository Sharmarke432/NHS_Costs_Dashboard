"""
tests/test_database_connection.py

Verifies that the DuckDB database has been built correctly and that both
`cost_records` (the full table) and `valid_cost_records` (the benchmark-
eligible view) are queryable and contain data.

Run with: pytest
"""

import pytest

from src.database import get_connection


def test_database_connection_opens():
    """get_connection() should succeed without raising, assuming the
    database has already been built via `python src/load_database.py`."""
    with get_connection() as con:
        assert con is not None


def test_cost_records_table_exists_and_has_rows():
    with get_connection() as con:
        count = con.execute("SELECT COUNT(*) FROM cost_records").fetchone()[0]
    assert count > 0


def test_valid_cost_records_view_exists_and_has_rows():
    with get_connection() as con:
        count = con.execute("SELECT COUNT(*) FROM valid_cost_records").fetchone()[0]
    assert count > 0


def test_valid_cost_records_is_subset_of_cost_records():
    """valid_cost_records excludes rows (e.g. 999 - Unknown, non-positive
    activity) so it should never contain MORE rows than the full table."""
    with get_connection() as con:
        total = con.execute("SELECT COUNT(*) FROM cost_records").fetchone()[0]
        valid = con.execute("SELECT COUNT(*) FROM valid_cost_records").fetchone()[0]
    assert valid <= total


def test_valid_cost_records_excludes_unknown_service():
    with get_connection() as con:
        unknown_count = con.execute(
            "SELECT COUNT(*) FROM valid_cost_records WHERE Service = '999 - Unknown'"
        ).fetchone()[0]
    assert unknown_count == 0


def test_missing_database_raises_clear_error(monkeypatch, tmp_path):
    """If the .duckdb file doesn't exist yet, get_connection() should raise
    a FileNotFoundError with a helpful message, not a cryptic DuckDB error."""
    import src.database as database_module

    fake_path = tmp_path / "does_not_exist.duckdb"
    monkeypatch.setattr(database_module, "DB_PATH", fake_path)

    with pytest.raises(FileNotFoundError, match="Run `python src/load_database.py`"):
        with database_module.get_connection():
            pass