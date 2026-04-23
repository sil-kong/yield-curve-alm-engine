import pytest

from yield_curve_alm_engine.risk.immunization import duration_gap_diagnostic


def test_duration_gap_diagnostic_reports_first_order_surplus_sensitivity() -> None:
    diagnostic = duration_gap_diagnostic(
        asset_value=100.0,
        liability_value=80.0,
        asset_modified_duration=5.0,
        liability_modified_duration=7.0,
    )

    assert diagnostic["duration_gap_years"] == pytest.approx(-2.0)
    assert diagnostic["asset_value_change_per_1bp_up"] == pytest.approx(-0.05)
    assert diagnostic["liability_value_change_per_1bp_up"] == pytest.approx(-0.056)
    assert diagnostic["surplus_change_per_1bp_up"] == pytest.approx(0.006)
