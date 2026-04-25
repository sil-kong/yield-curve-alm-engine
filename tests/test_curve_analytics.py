import math

import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.curve.analytics import (
    compute_curve_analytics,
    continuous_forward_rate,
    curve_curvature,
    curve_slope,
    discount_factor_to_zero_rate,
)


def _metric_value(table, metric: str) -> float:
    return float(table.loc[table["metric"] == metric, "value"].iloc[0])


def test_compute_curve_analytics_reports_slope_and_curvature() -> None:
    curve = ZeroCurve(
        maturities=[1.0, 2.0, 5.0, 10.0, 30.0],
        zero_rates=[0.02, 0.021, 0.025, 0.03, 0.035],
    )

    analytics = compute_curve_analytics(curve)

    assert {"metric", "value", "unit", "interpretation"}.issubset(analytics.columns)
    assert _metric_value(analytics, "slope_2y_10y") == pytest.approx(0.009)
    assert _metric_value(analytics, "curvature_2y_5y_10y") == pytest.approx(-0.001)
    assert _metric_value(analytics, "forward_5y_10y") == pytest.approx(0.035)
    assert 0.0 < _metric_value(analytics, "discount_factor_30y") < 1.0


def test_discount_factor_to_zero_rate() -> None:
    assert discount_factor_to_zero_rate(discount_factor=0.95, maturity=2.0) == pytest.approx(
        -math.log(0.95) / 2.0
    )


def test_discount_factor_to_zero_rate_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        discount_factor_to_zero_rate(0.0, 1.0)
    with pytest.raises(ValueError):
        discount_factor_to_zero_rate(0.95, 0.0)


def test_continuous_forward_rate_matches_flat_curve_rate() -> None:
    curve = ZeroCurve(maturities=[1.0, 10.0], zero_rates=[0.03, 0.03])

    assert continuous_forward_rate(curve, 1.0, 10.0) == pytest.approx(0.03)


def test_continuous_forward_rate_rejects_invalid_window() -> None:
    curve = ZeroCurve(maturities=[1.0, 10.0], zero_rates=[0.03, 0.03])

    with pytest.raises(ValueError):
        continuous_forward_rate(curve, 0.0, 10.0)
    with pytest.raises(ValueError):
        continuous_forward_rate(curve, 5.0, 5.0)


def test_curve_slope_and_curvature_helpers() -> None:
    curve = ZeroCurve(
        maturities=[1.0, 2.0, 5.0, 10.0, 30.0],
        zero_rates=[0.02, 0.021, 0.025, 0.03, 0.035],
    )

    assert curve_slope(curve) == pytest.approx(0.009)
    assert curve_curvature(curve) == pytest.approx(-0.001)


def test_curve_shape_helpers_reject_invalid_maturities() -> None:
    curve = ZeroCurve(maturities=[1.0, 10.0], zero_rates=[0.03, 0.03])

    with pytest.raises(ValueError):
        curve_slope(curve, 10.0, 2.0)
    with pytest.raises(ValueError):
        curve_curvature(curve, 5.0, 2.0, 10.0)
