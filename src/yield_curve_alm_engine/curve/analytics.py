"""Yield-curve analytics and curve-shape diagnostics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve


def _require_positive(value: float, label: str) -> None:
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be a finite positive number.")


def discount_factor_to_zero_rate(discount_factor: float, maturity: float) -> float:
    """Convert a discount factor into a continuously compounded zero rate.

    ``R(T) = -log(DF(T)) / T``
    """
    _require_positive(discount_factor, "discount_factor")
    _require_positive(maturity, "maturity")
    return -math.log(discount_factor) / maturity


def continuous_forward_rate(curve: ZeroCurve, start: float, end: float) -> float:
    """Compute the continuously compounded forward rate between two maturities.

    ``F(T1,T2) = -log(DF(T2) / DF(T1)) / (T2 - T1)``
    """
    _require_positive(start, "start")
    _require_positive(end, "end")
    if end <= start:
        raise ValueError("end must be greater than start.")

    start_discount_factor = curve.get_discount_factor(start)
    end_discount_factor = curve.get_discount_factor(end)
    return -math.log(end_discount_factor / start_discount_factor) / (end - start)


def curve_slope(
    curve: ZeroCurve,
    short_maturity: float = 2.0,
    long_maturity: float = 10.0,
) -> float:
    """Return ``R(long) - R(short)`` for the supplied curve."""
    _require_positive(short_maturity, "short_maturity")
    _require_positive(long_maturity, "long_maturity")
    if long_maturity <= short_maturity:
        raise ValueError("long_maturity must be greater than short_maturity.")

    return curve.get_zero_rate(long_maturity) - curve.get_zero_rate(short_maturity)


def curve_curvature(
    curve: ZeroCurve,
    short: float = 2.0,
    belly: float = 5.0,
    long: float = 10.0,
) -> float:
    """Return the simple ``2 * R(belly) - R(short) - R(long)`` curvature proxy."""
    _require_positive(short, "short")
    _require_positive(belly, "belly")
    _require_positive(long, "long")
    if not short < belly < long:
        raise ValueError("maturities must satisfy short < belly < long.")

    return 2.0 * curve.get_zero_rate(belly) - curve.get_zero_rate(short) - curve.get_zero_rate(long)


def _metric_row(metric: str, value: float, unit: str, interpretation: str) -> dict[str, float | str]:
    return {
        "metric": metric,
        "value": float(value),
        "unit": unit,
        "interpretation": interpretation,
    }


def compute_curve_analytics(curve: ZeroCurve) -> pd.DataFrame:
    """Return zero-curve and curve-shape diagnostics as a metric table."""
    rows = [
        _metric_row(
            "zero_rate_1y",
            curve.get_zero_rate(1.0),
            "decimal_rate",
            "Interpolated 1-year continuously compounded zero rate.",
        ),
        _metric_row(
            "zero_rate_2y",
            curve.get_zero_rate(2.0),
            "decimal_rate",
            "Interpolated 2-year continuously compounded zero rate.",
        ),
        _metric_row(
            "zero_rate_5y",
            curve.get_zero_rate(5.0),
            "decimal_rate",
            "Interpolated 5-year continuously compounded zero rate.",
        ),
        _metric_row(
            "zero_rate_10y",
            curve.get_zero_rate(10.0),
            "decimal_rate",
            "Interpolated 10-year continuously compounded zero rate.",
        ),
        _metric_row(
            "zero_rate_30y",
            curve.get_zero_rate(30.0),
            "decimal_rate",
            "Interpolated 30-year continuously compounded zero rate.",
        ),
        _metric_row(
            "slope_2y_10y",
            curve_slope(curve, 2.0, 10.0),
            "decimal_rate",
            "10-year zero rate minus 2-year zero rate.",
        ),
        _metric_row(
            "slope_5y_30y",
            curve_slope(curve, 5.0, 30.0),
            "decimal_rate",
            "30-year zero rate minus 5-year zero rate.",
        ),
        _metric_row(
            "curvature_2y_5y_10y",
            curve_curvature(curve, 2.0, 5.0, 10.0),
            "decimal_rate",
            "Simple 2s5s10s belly curvature proxy.",
        ),
        _metric_row(
            "forward_1y_5y",
            continuous_forward_rate(curve, 1.0, 5.0),
            "decimal_rate",
            "Continuously compounded forward rate between 1 and 5 years.",
        ),
        _metric_row(
            "forward_5y_10y",
            continuous_forward_rate(curve, 5.0, 10.0),
            "decimal_rate",
            "Continuously compounded forward rate between 5 and 10 years.",
        ),
        _metric_row(
            "forward_10y_30y",
            continuous_forward_rate(curve, 10.0, 30.0),
            "decimal_rate",
            "Continuously compounded forward rate between 10 and 30 years.",
        ),
        _metric_row(
            "discount_factor_10y",
            curve.get_discount_factor(10.0),
            "discount_factor",
            "10-year discount factor under continuous compounding.",
        ),
        _metric_row(
            "discount_factor_30y",
            curve.get_discount_factor(30.0),
            "discount_factor",
            "30-year discount factor under continuous compounding.",
        ),
    ]
    return pd.DataFrame(rows)
