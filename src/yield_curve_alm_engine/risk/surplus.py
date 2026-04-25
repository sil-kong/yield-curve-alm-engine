"""Balance-sheet surplus and stress-test analytics."""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond, price_bond, price_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import (
    liability_present_value,
    liability_risk_metrics,
)
from yield_curve_alm_engine.risk.immunization import estimate_parallel_surplus_impact


def asset_market_value(bonds: list[Bond], curve: ZeroCurve) -> float:
    """Return total asset market value for a bond portfolio."""
    return float(sum(price_bond(bond, curve) for bond in bonds))


def liability_value(liabilities: pd.DataFrame, curve: ZeroCurve) -> float:
    """Return present value of liability cash flows."""
    return liability_present_value(liabilities, curve)


def compute_balance_sheet(
    bonds: list[Bond],
    liabilities: pd.DataFrame,
    curve: ZeroCurve,
    scenario: str = "base",
) -> dict[str, float | str]:
    """Compute asset value, liability value and surplus."""
    assets = asset_market_value(bonds, curve)
    liability_pv = liability_value(liabilities, curve)
    return {
        "scenario": scenario,
        "asset_value": assets,
        "liability_value": liability_pv,
        "surplus": assets - liability_pv,
    }


def _change_pct(value: float, base_value: float) -> float:
    if np.isclose(base_value, 0.0):
        return np.nan
    return value / base_value - 1.0


def add_base_comparison(
    scenario_result: dict[str, float | str],
    base_result: dict[str, float | str],
) -> dict[str, float | str]:
    """Add changes versus the base balance sheet."""
    result = dict(scenario_result)
    for field in ["asset_value", "liability_value", "surplus"]:
        value = float(result[field])
        base_value = float(base_result[field])
        result[f"{field}_change"] = value - base_value
        result[f"{field}_change_pct"] = _change_pct(value, base_value)
    return result


def run_surplus_scenarios(
    bonds: list[Bond],
    liabilities: pd.DataFrame,
    base_curve: ZeroCurve,
    scenarios: dict[str, Callable[[ZeroCurve], ZeroCurve]],
    include_base: bool = True,
) -> pd.DataFrame:
    """Run deterministic curve stresses and return a surplus comparison table."""
    base_result = compute_balance_sheet(bonds, liabilities, base_curve, "base")
    rows: list[dict[str, float | str]] = []

    if include_base:
        rows.append(add_base_comparison(base_result, base_result))

    for scenario_name, scenario_function in scenarios.items():
        stressed_curve = scenario_function(base_curve)
        scenario_result = compute_balance_sheet(
            bonds,
            liabilities,
            stressed_curve,
            scenario_name,
        )
        rows.append(add_base_comparison(scenario_result, base_result))

    return pd.DataFrame(rows)


def _weighted_metric(table: pd.DataFrame, metric: str) -> float:
    weights = table["price"] / table["price"].sum()
    return float((weights * table[metric]).sum())


def parallel_surplus_shock_comparison(
    bonds: list[Bond],
    liabilities: pd.DataFrame,
    curve: ZeroCurve,
    shock_size: float = 0.0001,
) -> dict[str, float]:
    """Compare exact surplus revaluation with a first-order duration estimate.

    The shock is a parallel shift in continuously compounded zero rates. This
    helper is a base-case diagnostic, not a hedge optimizer or a replacement
    for full scenario analysis.
    """
    if not np.isfinite(shock_size) or np.isclose(shock_size, 0.0):
        raise ValueError("shock_size must be a finite non-zero rate shift.")

    base = compute_balance_sheet(bonds, liabilities, curve, scenario="base")
    shocked_curve = curve.with_zero_rates(
        curve.zero_rates + shock_size,
        name=f"parallel_{shock_size * 10_000:g}bp",
    )
    shocked = compute_balance_sheet(bonds, liabilities, shocked_curve, scenario="parallel")

    bond_table = price_bond_portfolio(bonds, curve)
    liability_metrics = liability_risk_metrics(liabilities, curve)
    asset_duration = _weighted_metric(bond_table, "modified_duration")
    liability_duration = float(liability_metrics["modified_duration"])

    estimated_surplus_change = estimate_parallel_surplus_impact(
        asset_value=float(base["asset_value"]),
        liability_value=float(base["liability_value"]),
        asset_duration=asset_duration,
        liability_duration=liability_duration,
        shock_size=shock_size,
    )
    exact_surplus_change = float(shocked["surplus"]) - float(base["surplus"])
    estimate_error = estimated_surplus_change - exact_surplus_change
    relative_error = 0.0
    if not np.isclose(exact_surplus_change, 0.0):
        relative_error = estimate_error / abs(exact_surplus_change)

    return {
        "parallel_shock_bps": shock_size * 10_000.0,
        "base_asset_value": float(base["asset_value"]),
        "base_liability_value": float(base["liability_value"]),
        "base_surplus": float(base["surplus"]),
        "shocked_asset_value": float(shocked["asset_value"]),
        "shocked_liability_value": float(shocked["liability_value"]),
        "shocked_surplus": float(shocked["surplus"]),
        "exact_asset_change": float(shocked["asset_value"]) - float(base["asset_value"]),
        "exact_liability_change": float(shocked["liability_value"])
        - float(base["liability_value"]),
        "exact_surplus_change": exact_surplus_change,
        "estimated_surplus_change": estimated_surplus_change,
        "estimate_error": estimate_error,
        "relative_error_vs_exact": relative_error,
    }


def parallel_surplus_shock_comparisons(
    bonds: list[Bond],
    liabilities: pd.DataFrame,
    curve: ZeroCurve,
    shock_sizes: tuple[float, ...] = (0.0001, 0.01, -0.01),
) -> pd.DataFrame:
    """Return exact-vs-duration surplus comparisons for several parallel shocks."""
    rows = [
        parallel_surplus_shock_comparison(
            bonds=bonds,
            liabilities=liabilities,
            curve=curve,
            shock_size=shock_size,
        )
        for shock_size in shock_sizes
    ]
    return pd.DataFrame(rows)


def compare_bond_sensitivities(
    bonds: list[Bond],
    base_curve: ZeroCurve,
    scenarios: dict[str, Callable[[ZeroCurve], ZeroCurve]],
) -> pd.DataFrame:
    """Return bond-level price changes under each stress scenario."""
    base_table = price_bond_portfolio(bonds, base_curve).set_index("bond_name")
    rows = []

    for scenario_name, scenario_function in scenarios.items():
        stressed_curve = scenario_function(base_curve)
        shocked_table = price_bond_portfolio(bonds, stressed_curve).set_index("bond_name")

        for bond_name, base_row in base_table.iterrows():
            shocked_price = float(shocked_table.loc[bond_name, "price"])
            base_price = float(base_row["price"])
            rows.append(
                {
                    "scenario": scenario_name,
                    "bond_name": bond_name,
                    "base_price": base_price,
                    "shocked_price": shocked_price,
                    "price_change": shocked_price - base_price,
                    "price_change_pct": _change_pct(shocked_price, base_price),
                    "macaulay_duration": float(base_row["macaulay_duration"]),
                    "modified_duration": float(base_row["modified_duration"]),
                    "convexity": float(base_row["convexity"]),
                }
            )

    return pd.DataFrame(rows)
