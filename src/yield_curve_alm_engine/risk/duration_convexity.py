"""Reusable present value, duration and convexity calculations."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from yield_curve_alm_engine.curve.base_curve import ZeroCurve


def _to_arrays(times: Iterable[float], cash_flows: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    time_array = np.asarray(list(times), dtype=float)
    cash_flow_array = np.asarray(list(cash_flows), dtype=float)

    if time_array.ndim != 1 or cash_flow_array.ndim != 1:
        raise ValueError("times and cash_flows must be one-dimensional.")
    if len(time_array) != len(cash_flow_array):
        raise ValueError("times and cash_flows must have the same length.")
    if len(time_array) == 0:
        raise ValueError("at least one cash flow is required.")
    if np.any(time_array <= 0):
        raise ValueError("cash-flow times must be strictly positive.")

    return time_array, cash_flow_array


def discounted_cash_flows(
    times: Iterable[float],
    cash_flows: Iterable[float],
    curve: ZeroCurve,
) -> np.ndarray:
    """Return discounted cash flows under the supplied curve."""
    time_array, cash_flow_array = _to_arrays(times, cash_flows)
    return cash_flow_array * curve.get_discount_factors(time_array)


def present_value_from_cash_flows(
    times: Iterable[float],
    cash_flows: Iterable[float],
    curve: ZeroCurve,
) -> float:
    """Return the present value of dated cash flows."""
    return float(np.sum(discounted_cash_flows(times, cash_flows, curve)))


def macaulay_duration(
    times: Iterable[float],
    cash_flows: Iterable[float],
    curve: ZeroCurve,
) -> float:
    """Return Macaulay duration in years."""
    time_array, cash_flow_array = _to_arrays(times, cash_flows)
    present_values = discounted_cash_flows(time_array, cash_flow_array, curve)
    total_value = float(np.sum(present_values))
    if np.isclose(total_value, 0.0):
        raise ValueError("duration is undefined for zero present value.")
    return float(np.sum(time_array * present_values) / total_value)


def modified_duration(
    times: Iterable[float],
    cash_flows: Iterable[float],
    curve: ZeroCurve,
) -> float:
    """Return modified duration for a parallel continuous zero-rate shift.

    With continuously compounded discount factors, modified duration equals
    Macaulay duration for sensitivity to a parallel shift of the zero curve.
    """
    return macaulay_duration(times, cash_flows, curve)


def convexity(
    times: Iterable[float],
    cash_flows: Iterable[float],
    curve: ZeroCurve,
) -> float:
    """Return continuous-compounding convexity with respect to a parallel shift."""
    time_array, cash_flow_array = _to_arrays(times, cash_flows)
    present_values = discounted_cash_flows(time_array, cash_flow_array, curve)
    total_value = float(np.sum(present_values))
    if np.isclose(total_value, 0.0):
        raise ValueError("convexity is undefined for zero present value.")
    return float(np.sum((time_array**2) * present_values) / total_value)
