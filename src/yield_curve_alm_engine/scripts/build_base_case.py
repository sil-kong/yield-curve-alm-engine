"""Build and save the stylized ALM base case."""

from __future__ import annotations

import argparse

import pandas as pd

from yield_curve_alm_engine.config import OUTPUTS
from yield_curve_alm_engine.instruments.bonds import price_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import (
    create_stylized_liability_schedule,
    liability_risk_metrics,
    liability_value_table,
)
from yield_curve_alm_engine.risk.surplus import compute_balance_sheet
from yield_curve_alm_engine.scripts.common import add_input_arguments, load_bonds, load_curve


def _currency(value: float) -> str:
    return f"{value:,.0f}"


def _weighted_metric(table: pd.DataFrame, metric: str) -> float:
    weights = table["price"] / table["price"].sum()
    return float((weights * table[metric]).sum())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ALM base case.")
    add_input_arguments(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    curve = load_curve(args.curve_csv)
    bonds = load_bonds(args.bonds_csv)
    liabilities = create_stylized_liability_schedule()

    curve_table = curve.to_frame()
    bond_table = price_bond_portfolio(bonds, curve)
    liability_table = liability_value_table(liabilities, curve)
    balance_sheet = compute_balance_sheet(bonds, liabilities, curve, scenario="base")
    liability_metrics = liability_risk_metrics(liabilities, curve)

    summary = {
        **balance_sheet,
        "asset_macaulay_duration": _weighted_metric(bond_table, "macaulay_duration"),
        "asset_modified_duration": _weighted_metric(bond_table, "modified_duration"),
        "asset_convexity": _weighted_metric(bond_table, "convexity"),
        "liability_macaulay_duration": liability_metrics["macaulay_duration"],
        "liability_modified_duration": liability_metrics["modified_duration"],
        "liability_convexity": liability_metrics["convexity"],
    }
    summary_table = pd.DataFrame([summary])

    curve_table.to_csv(OUTPUTS / "base_curve.csv", index=False)
    bond_table.to_csv(OUTPUTS / "base_case_bonds.csv", index=False)
    liability_table.to_csv(OUTPUTS / "base_case_liabilities.csv", index=False)
    summary_table.to_csv(OUTPUTS / "base_case_summary.csv", index=False)

    print("\nBase Case Balance Sheet")
    print("-----------------------")
    print(f"Asset market value : {_currency(float(balance_sheet['asset_value']))}")
    print(f"Liability PV       : {_currency(float(balance_sheet['liability_value']))}")
    print(f"Surplus            : {_currency(float(balance_sheet['surplus']))}")
    print()

    display_columns = [
        "bond_name",
        "price",
        "macaulay_duration",
        "convexity",
    ]
    print("Bond Portfolio")
    print(bond_table[display_columns].to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print(f"\nSaved base-case outputs to: {OUTPUTS}")


if __name__ == "__main__":
    main()
