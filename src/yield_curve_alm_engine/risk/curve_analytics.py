"""Compatibility re-export for curve analytics.

Curve-level analytics live in :mod:`yield_curve_alm_engine.curve.analytics`.
This module remains to avoid breaking older imports.
"""

from yield_curve_alm_engine.curve.analytics import (
    compute_curve_analytics,
    continuous_forward_rate,
    curve_curvature,
    curve_slope,
    discount_factor_to_zero_rate,
)

__all__ = [
    "compute_curve_analytics",
    "continuous_forward_rate",
    "curve_curvature",
    "curve_slope",
    "discount_factor_to_zero_rate",
]
