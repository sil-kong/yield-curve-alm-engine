"""Simple yield-curve diagnostics for ALM reporting."""

from __future__ import annotations

import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve


def compute_curve_analytics(curve: ZeroCurve) -> pd.DataFrame:
    """Return compact zero-curve diagnostics as a metric table.

    The diagnostics are deliberately simple: selected zero rates, common slope
    measures, a 2s5s10s curvature proxy and discount-factor endpoints. They are
    intended for reporting and sanity checks, not for curve calibration.
    """
    rate_1y = curve.get_zero_rate(1.0)
    rate_2y = curve.get_zero_rate(2.0)
    rate_5y = curve.get_zero_rate(5.0)
    rate_10y = curve.get_zero_rate(10.0)
    rate_30y = curve.get_zero_rate(30.0)

    rows = [
        {
            "metric": "zero_rate_1y",
            "value": rate_1y,
            "unit": "decimal_rate",
            "interpretation": "Interpolated 1-year continuously compounded zero rate.",
        },
        {
            "metric": "zero_rate_10y",
            "value": rate_10y,
            "unit": "decimal_rate",
            "interpretation": "Interpolated 10-year continuously compounded zero rate.",
        },
        {
            "metric": "zero_rate_30y",
            "value": rate_30y,
            "unit": "decimal_rate",
            "interpretation": "Interpolated 30-year continuously compounded zero rate.",
        },
        {
            "metric": "slope_2y_10y",
            "value": rate_10y - rate_2y,
            "unit": "decimal_rate",
            "interpretation": "10-year zero rate minus 2-year zero rate.",
        },
        {
            "metric": "slope_5y_30y",
            "value": rate_30y - rate_5y,
            "unit": "decimal_rate",
            "interpretation": "30-year zero rate minus 5-year zero rate.",
        },
        {
            "metric": "curvature_2y_5y_10y",
            "value": 2.0 * rate_5y - rate_2y - rate_10y,
            "unit": "decimal_rate",
            "interpretation": "Simple 2s5s10s belly curvature proxy.",
        },
        {
            "metric": "discount_factor_10y",
            "value": curve.get_discount_factor(10.0),
            "unit": "discount_factor",
            "interpretation": "10-year discount factor under continuous compounding.",
        },
        {
            "metric": "discount_factor_30y",
            "value": curve.get_discount_factor(30.0),
            "unit": "discount_factor",
            "interpretation": "30-year discount factor under continuous compounding.",
        },
    ]
    return pd.DataFrame(rows)
