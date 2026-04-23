"""Stylized liability cash-flow schedules."""

from __future__ import annotations

import numpy as np
import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.risk.duration_convexity import (
    convexity,
    macaulay_duration,
    modified_duration,
    present_value_from_cash_flows,
)


def create_stylized_liability_schedule(
    years: int = 20,
    base_cash_flow: float = 320_000.0,
) -> pd.DataFrame:
    """Create annual synthetic liability outflows with a mid-horizon hump."""
    if years <= 0:
        raise ValueError("years must be positive.")
    if base_cash_flow <= 0:
        raise ValueError("base_cash_flow must be positive.")

    times = np.arange(1, years + 1, dtype=float)
    trend = 1.0 + 0.025 * times
    hump = 1.0 + 0.55 * np.exp(-0.5 * ((times - 10.0) / 4.0) ** 2)
    runoff = np.where(times > 14.0, 1.0 - 0.035 * (times - 14.0), 1.0)
    cash_flows = base_cash_flow * trend * hump * np.clip(runoff, 0.70, None)

    return pd.DataFrame(
        {
            "time_years": times,
            "cash_flow": cash_flows,
        }
    )


def liability_present_value(liabilities: pd.DataFrame, curve: ZeroCurve) -> float:
    """Present value liability outflows as positive obligations."""
    return present_value_from_cash_flows(
        liabilities["time_years"],
        liabilities["cash_flow"],
        curve,
    )


def liability_value_table(liabilities: pd.DataFrame, curve: ZeroCurve) -> pd.DataFrame:
    """Add discount factors and present values to a liability schedule."""
    table = liabilities.copy()
    table["discount_factor"] = curve.get_discount_factors(table["time_years"])
    table["present_value"] = table["cash_flow"] * table["discount_factor"]
    return table


def liability_risk_metrics(liabilities: pd.DataFrame, curve: ZeroCurve) -> dict[str, float]:
    """Compute liability PV, duration and convexity."""
    times = liabilities["time_years"]
    cash_flows = liabilities["cash_flow"]
    return {
        "liability_value": liability_present_value(liabilities, curve),
        "macaulay_duration": macaulay_duration(times, cash_flows, curve),
        "modified_duration": modified_duration(times, cash_flows, curve),
        "convexity": convexity(times, cash_flows, curve),
    }
