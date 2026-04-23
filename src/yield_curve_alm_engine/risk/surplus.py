"""Balance-sheet surplus and stress-test analytics."""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond, price_bond, price_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import liability_present_value


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
