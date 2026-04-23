"""Deterministic stress scenarios for zero-coupon curves."""

from __future__ import annotations

from typing import Callable

import numpy as np

from yield_curve_alm_engine.curve.base_curve import ZeroCurve

ScenarioFunction = Callable[[ZeroCurve], ZeroCurve]


def _bps_to_rate(basis_points: np.ndarray | float) -> np.ndarray | float:
    return basis_points / 10_000.0


def apply_rate_shock(curve: ZeroCurve, shock_bps: np.ndarray, name: str) -> ZeroCurve:
    """Apply maturity-specific shocks, expressed in basis points, to a curve."""
    if len(shock_bps) != len(curve.maturities):
        raise ValueError("shock_bps must have one entry per curve maturity.")
    stressed_rates = curve.zero_rates + _bps_to_rate(shock_bps)
    return curve.with_zero_rates(stressed_rates, name=name)


def parallel_up_100bps(curve: ZeroCurve) -> ZeroCurve:
    """Add 100 bps to every zero rate."""
    shock_bps = np.full(len(curve.maturities), 100.0)
    return apply_rate_shock(curve, shock_bps, "parallel_up_100bps")


def parallel_down_100bps(curve: ZeroCurve) -> ZeroCurve:
    """Subtract 100 bps from every zero rate."""
    shock_bps = np.full(len(curve.maturities), -100.0)
    return apply_rate_shock(curve, shock_bps, "parallel_down_100bps")


def steepener(curve: ZeroCurve) -> ZeroCurve:
    """Lower short rates and raise long rates with a linear shock profile."""
    shock_bps = np.interp(
        curve.maturities,
        [curve.maturities[0], curve.maturities[-1]],
        [-50.0, 75.0],
    )
    return apply_rate_shock(curve, shock_bps, "steepener")


def flattener(curve: ZeroCurve) -> ZeroCurve:
    """Raise short rates and lower long rates with a linear shock profile."""
    shock_bps = np.interp(
        curve.maturities,
        [curve.maturities[0], curve.maturities[-1]],
        [50.0, -75.0],
    )
    return apply_rate_shock(curve, shock_bps, "flattener")


def curvature_shock(curve: ZeroCurve) -> ZeroCurve:
    """Raise belly rates while leaving the short and long ends mostly unchanged."""
    center_years = 7.0
    width_years = 5.0
    shock_bps = 60.0 * np.exp(-0.5 * ((curve.maturities - center_years) / width_years) ** 2)
    return apply_rate_shock(curve, shock_bps, "curvature_shock")


def get_stress_scenarios() -> dict[str, ScenarioFunction]:
    """Return the deterministic stress scenario registry."""
    return {
        "parallel_up_100bps": parallel_up_100bps,
        "parallel_down_100bps": parallel_down_100bps,
        "steepener": steepener,
        "flattener": flattener,
        "curvature_shock": curvature_shock,
    }
