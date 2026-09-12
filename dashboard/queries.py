"""
dashboard/queries.py

Parameterised DuckDB query functions for the NHS Cost Intelligence dashboard.

All filter values are passed with `?` placeholders -- never string-interpolated --
to avoid SQL injection and keep queries safe for user-controlled inputs.

Central metric:
    activity_weighted_unit_cost = SUM(Unit_Cost * Activity) / NULLIF(SUM(Activity), 0)

This is a descriptive benchmark, not an efficiency ranking. See project
guardrails: never claim high cost implies waste or inefficiency.
"""

from typing import Optional

import pandas as pd

from src.database import get_connection


def get_filter_options() -> dict:
    """Returns distinct Department and Mapping_Pot values for dashboard selectboxes."""
    with get_connection() as con:
        departments = con.execute(
            """
            SELECT DISTINCT Department
            FROM valid_cost_records
            WHERE Department IS NOT NULL
            ORDER BY Department
            """
        ).df()["Department"].tolist()

        mapping_pots = con.execute(
            """
            SELECT DISTINCT Mapping_Pot
            FROM valid_cost_records
            WHERE Mapping_Pot IS NOT NULL
            ORDER BY Mapping_Pot
            """
        ).df()["Mapping_Pot"].tolist()

    return {"departments": departments, "mapping_pots": mapping_pots}


def get_service_benchmarks(
    min_activity: int = 50,
    min_provider_count: int = 3,
    department: Optional[str] = None,
    mapping_pot: Optional[str] = None,
    limit: int = 15,
) -> pd.DataFrame:
    """
    Top eligible services ranked by activity-weighted unit cost.

    Applies minimum activity and minimum provider-count thresholds in HAVING,
    plus optional Department / Mapping_Pot filters, all parameterised.
    """
    filters = []
    params: list = []

    if department:
        filters.append("Department = ?")
        params.append(department)
    if mapping_pot:
        filters.append("Mapping_Pot = ?")
        params.append(mapping_pot)

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    sql = f"""
        SELECT
            Service AS service,
            SUM(Activity) AS total_activity,
            COUNT(DISTINCT Provider) AS provider_count,
            SUM(Unit_Cost * Activity) / NULLIF(SUM(Activity), 0) AS activity_weighted_unit_cost,
            MEDIAN(Unit_Cost) AS median_unit_cost,
            AVG(Unit_Cost) AS simple_mean_unit_cost,
            SUM(Actual_Cost) / NULLIF(SUM(Activity), 0) AS actual_cost_per_activity
        FROM valid_cost_records
        {where_clause}
        GROUP BY Service
        HAVING SUM(Activity) >= ?
           AND COUNT(DISTINCT Provider) >= ?
        ORDER BY activity_weighted_unit_cost DESC
        LIMIT ?
    """
    params.extend([min_activity, min_provider_count, limit])

    with get_connection() as con:
        return con.execute(sql, params).df()


def get_provider_benchmarks(service: str, min_activity: int = 5) -> pd.DataFrame:
    """Provider-level activity-weighted cost for a single service, for drill-down views."""
    sql = """
        SELECT
            Provider AS provider,
            SUM(Activity) AS total_activity,
            SUM(Unit_Cost * Activity) / NULLIF(SUM(Activity), 0) AS activity_weighted_unit_cost,
            SUM(Actual_Cost) AS total_actual_cost,
            MEDIAN(Unit_Cost) AS median_unit_cost
        FROM valid_cost_records
        WHERE Service = ?
        GROUP BY Provider
        HAVING SUM(Activity) >= ?
        ORDER BY activity_weighted_unit_cost DESC
    """
    with get_connection() as con:
        return con.execute(sql, [service, min_activity]).df()


def get_service_variation(
    min_activity: int = 50,
    min_provider_count: int = 3,
    limit: int = 15,
) -> pd.DataFrame:
    """Robust variation ranking using median and IQR rather than raw mean."""
    sql = """
        SELECT
            Service AS service,
            SUM(Activity) AS total_activity,
            COUNT(DISTINCT Provider) AS provider_count,
            MEDIAN(Unit_Cost) AS median_unit_cost,
            QUANTILE_CONT(Unit_Cost, 0.75) - QUANTILE_CONT(Unit_Cost, 0.25) AS iqr_unit_cost
        FROM valid_cost_records
        GROUP BY Service
        HAVING SUM(Activity) >= ?
           AND COUNT(DISTINCT Provider) >= ?
        ORDER BY iqr_unit_cost DESC
        LIMIT ?
    """
    with get_connection() as con:
        return con.execute(sql, [min_activity, min_provider_count, limit]).df()


def get_ncci_summary() -> pd.DataFrame:
    """Quantile summary of NCCI across valid records."""
    sql = """
        SELECT
            MEDIAN(NCCI) AS median_ncci,
            QUANTILE_CONT(NCCI, 0.25) AS p25_ncci,
            QUANTILE_CONT(NCCI, 0.75) AS p75_ncci,
            QUANTILE_CONT(NCCI, 0.99) AS p99_ncci,
            AVG(NCCI) AS mean_ncci
        FROM valid_cost_records
        WHERE NCCI IS NOT NULL
    """
    with get_connection() as con:
        return con.execute(sql).df()


def get_quality_summary() -> pd.DataFrame:
    """Counts of data-quality flags on the FULL table (including 999 - Unknown)."""
    sql = """
        SELECT
            SUM(CASE WHEN Service = '999 - Unknown' THEN 1 ELSE 0 END) AS unknown_service_rows,
            SUM(CASE WHEN Actual_Cost < 0 THEN 1 ELSE 0 END) AS negative_actual_cost_rows,
            SUM(CASE WHEN Expected_Cost <= 0 THEN 1 ELSE 0 END) AS non_positive_expected_cost_rows,
            SUM(CASE WHEN NCCI <= 0 THEN 1 ELSE 0 END) AS non_positive_ncci_rows,
            SUM(CASE WHEN Activity <= 0 THEN 1 ELSE 0 END) AS non_positive_activity_rows,
            COUNT(*) AS total_rows
        FROM cost_records
    """
    with get_connection() as con:
        return con.execute(sql).df()