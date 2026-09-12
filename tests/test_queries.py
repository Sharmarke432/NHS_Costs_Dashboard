"""
tests/test_queries.py

Minimal coverage for the service benchmark query, per project guardrails:
- returns non-empty output under default thresholds
- every returned service meets the activity threshold
- every returned service meets the provider-count threshold
- no returned activity-weighted cost is null

Run with: pytest
"""

import pytest

from dashboard.queries import get_service_benchmarks


DEFAULT_MIN_ACTIVITY = 50
DEFAULT_MIN_PROVIDER_COUNT = 3


@pytest.fixture(scope="module")
def default_benchmarks():
    return get_service_benchmarks(
        min_activity=DEFAULT_MIN_ACTIVITY,
        min_provider_count=DEFAULT_MIN_PROVIDER_COUNT,
        limit=15,
    )


def test_returns_non_empty_under_default_thresholds(default_benchmarks):
    assert len(default_benchmarks) > 0


def test_every_row_meets_activity_threshold(default_benchmarks):
    assert (default_benchmarks["total_activity"] >= DEFAULT_MIN_ACTIVITY).all()


def test_every_row_meets_provider_count_threshold(default_benchmarks):
    assert (default_benchmarks["provider_count"] >= DEFAULT_MIN_PROVIDER_COUNT).all()


def test_no_null_activity_weighted_cost(default_benchmarks):
    assert default_benchmarks["activity_weighted_unit_cost"].notna().all()


def test_higher_provider_threshold_returns_subset_or_equal():
    loose = get_service_benchmarks(min_activity=50, min_provider_count=1, limit=100)
    strict = get_service_benchmarks(min_activity=50, min_provider_count=10, limit=100)
    assert set(strict["service"]).issubset(set(loose["service"]))