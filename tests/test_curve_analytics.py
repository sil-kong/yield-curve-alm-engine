import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.risk.curve_analytics import compute_curve_analytics


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
    assert 0.0 < _metric_value(analytics, "discount_factor_30y") < 1.0
