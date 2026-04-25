"""Build and save the stylized ALM base case."""

from __future__ import annotations

import argparse

import pandas as pd

from yield_curve_alm_engine.config import OUTPUTS
from yield_curve_alm_engine.instruments.bonds import price_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import liability_risk_metrics, liability_value_table
from yield_curve_alm_engine.risk.immunization import duration_gap_diagnostic
from yield_curve_alm_engine.risk.curve_analytics import compute_curve_analytics
from yield_curve_alm_engine.risk.surplus import (
    compute_balance_sheet,
    parallel_surplus_shock_comparison,
)
from yield_curve_alm_engine.scripts.common import (
    add_input_arguments,
    load_bonds,
    load_curve,
    load_liabilities,
)


def _currency(value: float) -> str:
    return f"{value:,.0f}"


def _weighted_metric(table: pd.DataFrame, metric: str) -> float:
    weights = table["price"] / table["price"].sum()
    return float((weights * table[metric]).sum())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ALM base case.")
    add_input_arguments(parser)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    curve = load_curve(args.curve_csv)
    bonds = load_bonds(args.bonds_csv)
    liabilities = load_liabilities(args.liabilities_csv)

    curve_table = curve.to_frame()
    bond_table = price_bond_portfolio(bonds, curve)
    liability_table = liability_value_table(liabilities, curve)
    balance_sheet = compute_balance_sheet(bonds, liabilities, curve, scenario="base")
    liability_metrics = liability_risk_metrics(liabilities, curve)
    curve_analytics = compute_curve_analytics(curve)
    shock_comparison = parallel_surplus_shock_comparison(bonds, liabilities, curve)

    asset_macaulay_duration = _weighted_metric(bond_table, "macaulay_duration")
    asset_modified_duration = _weighted_metric(bond_table, "modified_duration")
    asset_convexity = _weighted_metric(bond_table, "convexity")
    diagnostic = duration_gap_diagnostic(
        asset_value=float(balance_sheet["asset_value"]),
        liability_value=float(balance_sheet["liability_value"]),
        asset_modified_duration=asset_modified_duration,
        liability_modified_duration=liability_metrics["modified_duration"],
    )

    summary = {
        **balance_sheet,
        "asset_macaulay_duration": asset_macaulay_duration,
        "asset_modified_duration": asset_modified_duration,
        "asset_convexity": asset_convexity,
        "liability_macaulay_duration": liability_metrics["macaulay_duration"],
        "liability_modified_duration": liability_metrics["modified_duration"],
        "liability_convexity": liability_metrics["convexity"],
        "parallel_1bp_exact_surplus_change": shock_comparison["exact_surplus_change"],
        "parallel_1bp_estimated_surplus_change": shock_comparison["estimated_surplus_change"],
        "parallel_1bp_estimate_error": shock_comparison["estimate_error"],
        **diagnostic,
    }
    summary_table = pd.DataFrame([summary])

    curve_table.to_csv(OUTPUTS / "base_curve.csv", index=False)
    bond_table.to_csv(OUTPUTS / "base_case_bonds.csv", index=False)
    liability_table.to_csv(OUTPUTS / "base_case_liabilities.csv", index=False)
    summary_table.to_csv(OUTPUTS / "base_case_summary.csv", index=False)
    curve_analytics.to_csv(OUTPUTS / "base_case_curve_analytics.csv", index=False)

    print("\nBase Case Balance Sheet")
    print("-----------------------")
    print(f"Asset market value : {_currency(float(balance_sheet['asset_value']))}")
    print(f"Liability PV       : {_currency(float(balance_sheet['liability_value']))}")
    print(f"Surplus            : {_currency(float(balance_sheet['surplus']))}")
    print(f"Duration gap       : {diagnostic['duration_gap_years']:,.2f} years")
    print(f"Surplus +1bp approx: {diagnostic['surplus_change_per_1bp_up']:,.0f}")
    print(f"Surplus +1bp exact : {shock_comparison['exact_surplus_change']:,.0f}")
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
