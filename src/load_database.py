"""
src/load_database.py

Builds the DuckDB database for the NHS Cost Intelligence project.

Responsibilities:
1. Read the row-level processed CSV.
2. Create data/processed/nhs_costs.duckdb.
3. Create `cost_records` as the full imported table (nothing deleted).
4. Validate that all expected columns exist.
5. Create `valid_cost_records` as the benchmark-eligible view
   (excludes 999 - Unknown, non-positive activity, nulls) without
   destructively removing anything from `cost_records`.

Run from the repository root:
    python src/load_database.py
"""

from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# IMPORTANT: update this to your actual processed CSV filename.
# This is the single line you must change to match your repository.
# ---------------------------------------------------------------------------
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "nhs_ncc_clean.csv"

DB_PATH = PROJECT_ROOT / "data" / "processed" / "nhs_costs.duckdb"

REQUIRED_COLUMNS = {
    "Provider", "Mapping_Pot", "Service", "Department",
    "Activity", "Unit_Cost", "Actual_Cost", "Expected_Cost",
    "Variance", "NCCI", "Variance_Percent",
}


def validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}. "
            f"Found columns: {sorted(df.columns.tolist())}"
        )


def build_database(csv_path: Path = CSV_PATH, db_path: Path = DB_PATH) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed CSV not found at {csv_path}. "
            "Update CSV_PATH in src/load_database.py to match your real file."
        )

    print(f"Reading processed CSV from: {csv_path}")
    df = pd.read_csv(csv_path)
    validate_columns(df)
    print(f"Loaded {len(df):,} rows, {len(df.columns)} columns.")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        db_path.unlink()

    con = duckdb.connect(str(db_path))
    try:
        con.register("df_view", df)
        con.execute("CREATE OR REPLACE TABLE cost_records AS SELECT * FROM df_view")

        con.execute(
            """
            CREATE OR REPLACE VIEW valid_cost_records AS
            SELECT *
            FROM cost_records
            WHERE Activity > 0
              AND Unit_Cost IS NOT NULL
              AND Service IS NOT NULL
              AND Service <> '999 - Unknown'
            """
        )

        total = con.execute("SELECT COUNT(*) FROM cost_records").fetchone()[0]
        valid = con.execute("SELECT COUNT(*) FROM valid_cost_records").fetchone()[0]
        print(f"cost_records: {total:,} rows")
        print(f"valid_cost_records: {valid:,} rows ({total - valid:,} excluded)")
    finally:
        con.close()

    print(f"Database written to: {db_path}")


if __name__ == "__main__":
    build_database()