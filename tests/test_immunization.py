import pytest

from yield_curve_alm_engine.risk.immunization import (
    compute_duration_gap,
    duration_gap_diagnostic,
    estimate_parallel_surplus_impact,
    solve_two_bond_immunization,
)


def test_compute_duration_gap_uses_liability_to_asset_scaling() -> None:
    gap = compute_duration_gap(
        asset_value=100.0,
        liability_value=80.0,
        asset_duration=5.0,
        liability_duration=7.0,
    )

    assert gap == pytest.approx(-0.6)


def test_estimate_parallel_surplus_impact_is_first_order_difference() -> None:
    impact = estimate_parallel_surplus_impact(
        asset_value=100.0,
        liability_value=80.0,
        asset_duration=5.0,
        liability_duration=7.0,
        shock_size=0.0001,
    )

    assert impact == pytest.approx(0.006)


def test_duration_gap_diagnostic_reports_first_order_surplus_sensitivity() -> None:
    diagnostic = duration_gap_diagnostic(
        asset_value=100.0,
        liability_value=80.0,
        asset_modified_duration=5.0,
        liability_modified_duration=7.0,
    )

    assert diagnostic["duration_gap_years"] == pytest.approx(-0.6)
    assert diagnostic["asset_liability_duration_difference"] == pytest.approx(-2.0)
    assert diagnostic["asset_value_change_per_1bp_up"] == pytest.approx(-0.05)
    assert diagnostic["liability_value_change_per_1bp_up"] == pytest.approx(-0.056)
    assert diagnostic["surplus_change_per_1bp_up"] == pytest.approx(0.006)


def test_solve_two_bond_immunization_matches_target_value_and_duration() -> None:
    solution = solve_two_bond_immunization(
        short_bond_metrics={"modified_duration": 2.0},
        long_bond_metrics={"modified_duration": 10.0},
        target_value=100.0,
        target_duration=6.0,
    )

    assert solution["short_weight"] == pytest.approx(50.0)
    assert solution["long_weight"] == pytest.approx(50.0)
    assert solution["portfolio_value"] == pytest.approx(100.0)
    assert solution["portfolio_duration"] == pytest.approx(6.0)
    assert solution["duration_error"] == pytest.approx(0.0)
