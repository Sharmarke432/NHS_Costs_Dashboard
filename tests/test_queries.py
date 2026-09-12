"""
tests/test_queries.py

Minimal coverage for the service benchmark query, per project guardrails:
- returns non-empty output under default thresholds
- every returned service meets the activity threshold
- every returned service meets the provider-count threshold
- no returned activity-weighted cost is null
- raising the provider-count threshold only removes services, never adds new ones

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
    """
    Raising min_provider_count can only shrink the ELIGIBLE population, never
    add new eligible services. We must compare full eligible sets here, not
    top-N slices -- a top-100-by-cost list can differ completely between two
    thresholds even though the underlying eligibility is a strict subset,
    because LIMIT re-ranks a different population each time.
    """
    very_high_limit = 100_000  # effectively "no limit", to get the full eligible set

    loose = get_service_benchmarks(
        min_activity=50, min_provider_count=1, limit=very_high_limit
    )
    strict = get_service_benchmarks(
        min_activity=50, min_provider_count=10, limit=very_high_limit
    )
    assert set(strict["service"]).issubset(set(loose["service"]))


def test_higher_provider_threshold_never_increases_eligible_count():
    """A softer, always-true sanity check: raising the threshold should
    never increase (and will typically decrease) the number of eligible
    services, regardless of LIMIT/ranking behaviour."""
    very_high_limit = 100_000

    loose = get_service_benchmarks(
        min_activity=50, min_provider_count=1, limit=very_high_limit
    )
    strict = get_service_benchmarks(
        min_activity=50, min_provider_count=10, limit=very_high_limit
    )
    assert len(strict) <= len(loose)