"""Build and save the stylized ALM base case."""

from __future__ import annotations

import argparse

import pandas as pd

from yield_curve_alm_engine.config import OUTPUTS
from yield_curve_alm_engine.curve.analytics import compute_curve_analytics
from yield_curve_alm_engine.instruments.bonds import price_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import liability_risk_metrics, liability_value_table
from yield_curve_alm_engine.risk.immunization import duration_gap_diagnostic
from yield_curve_alm_engine.risk.surplus import (
    compute_balance_sheet,
    parallel_surplus_shock_comparisons,
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


def _shock_row(shock_comparisons: pd.DataFrame, shock_bps: float) -> pd.Series:
    matches = shock_comparisons[
        shock_comparisons["parallel_shock_bps"].round(8) == round(shock_bps, 8)
    ]
    if matches.empty:
        raise ValueError(f"missing parallel shock comparison for {shock_bps:g} bps.")
    return matches.iloc[0]


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
    shock_comparisons = parallel_surplus_shock_comparisons(bonds, liabilities, curve)
    shock_1bp = _shock_row(shock_comparisons, 1.0)
    shock_up_100bps = _shock_row(shock_comparisons, 100.0)
    shock_down_100bps = _shock_row(shock_comparisons, -100.0)

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
        "parallel_1bp_exact_surplus_change": shock_1bp["exact_surplus_change"],
        "parallel_1bp_estimated_surplus_change": shock_1bp["estimated_surplus_change"],
        "parallel_1bp_estimate_error": shock_1bp["estimate_error"],
        "surplus_change_parallel_up_100bps": shock_up_100bps["exact_surplus_change"],
        "surplus_change_parallel_down_100bps": shock_down_100bps["exact_surplus_change"],
        "duration_approx_surplus_change_up_100bps": shock_up_100bps[
            "estimated_surplus_change"
        ],
        "duration_approx_surplus_change_down_100bps": shock_down_100bps[
            "estimated_surplus_change"
        ],
        "duration_approx_error_up_100bps": shock_up_100bps["estimate_error"],
        "duration_approx_error_down_100bps": shock_down_100bps["estimate_error"],
        **diagnostic,
    }
    summary_table = pd.DataFrame([summary])

    curve_table.to_csv(OUTPUTS / "base_curve.csv", index=False)
    bond_table.to_csv(OUTPUTS / "base_case_bonds.csv", index=False)
    liability_table.to_csv(OUTPUTS / "base_case_liabilities.csv", index=False)
    summary_table.to_csv(OUTPUTS / "base_case_summary.csv", index=False)
    curve_analytics.to_csv(OUTPUTS / "base_case_curve_analytics.csv", index=False)
    shock_comparisons.to_csv(OUTPUTS / "base_case_shock_comparison.csv", index=False)

    print("\nBase Case Balance Sheet")
    print("-----------------------")
    print(f"Asset market value : {_currency(float(balance_sheet['asset_value']))}")
    print(f"Liability PV       : {_currency(float(balance_sheet['liability_value']))}")
    print(f"Surplus            : {_currency(float(balance_sheet['surplus']))}")
    print(f"Duration gap       : {diagnostic['duration_gap_years']:,.2f} years")
    print("Parallel Shock Comparison")
    for row in shock_comparisons.itertuples(index=False):
        print(
            f"  {row.parallel_shock_bps:+,.0f} bps "
            f"exact={row.exact_surplus_change:,.0f}, "
            f"duration_estimate={row.estimated_surplus_change:,.0f}, "
            f"error={row.estimate_error:,.0f}"
        )
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
