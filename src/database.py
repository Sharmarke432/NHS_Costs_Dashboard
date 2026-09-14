"""
src/database.py

Read-only connection helper for the NHS Cost Intelligence DuckDB database.
"""

from pathlib import Path
from contextlib import contextmanager

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "processed" / "nhs_costs.duckdb"


@contextmanager
def get_connection():
    """
    Opens the NHS costs DuckDB database in read-only mode.

    Raises a clear error if the database has not been built yet
    (i.e. src/load_database.py has not been run).
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run `python src/load_database.py` from the repository root first."
        )

    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        yield con
    finally:
        con.close()