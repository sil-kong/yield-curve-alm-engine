"""Plot curve scenarios and ALM stress-test results."""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from yield_curve_alm_engine.config import OUTPUTS
from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.curve.shocks import get_stress_scenarios
from yield_curve_alm_engine.instruments.bonds import Bond
from yield_curve_alm_engine.risk.cashflow_matching import build_cashflow_gap_report
from yield_curve_alm_engine.risk.key_rate import compute_asset_liability_key_rate_report
from yield_curve_alm_engine.risk.surplus import run_surplus_scenarios
from yield_curve_alm_engine.scripts.common import (
    add_input_arguments,
    collect_asset_cash_flows,
    load_bonds,
    load_curve,
    load_liabilities,
)


def plot_curve_scenarios(base_curve: ZeroCurve) -> None:
    """Plot base and stressed zero curves."""
    scenarios = get_stress_scenarios()

    fig, ax = plt.subplots(figsize=(10, 6))
    base_table = base_curve.to_frame()
    ax.plot(
        base_table["maturity_years"],
        base_table["zero_rate"] * 100.0,
        marker="o",
        linewidth=2.2,
        label="base",
    )

    for scenario_name, scenario_function in scenarios.items():
        stressed_curve = scenario_function(base_curve)
        stressed_table = stressed_curve.to_frame()
        ax.plot(
            stressed_table["maturity_years"],
            stressed_table["zero_rate"] * 100.0,
            marker="o",
            linewidth=1.4,
            alpha=0.85,
            label=scenario_name,
        )

    ax.set_title("Base and Stressed Zero-Coupon Curves")
    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Continuously compounded zero rate (%)")
    ax.grid(True, alpha=0.30)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUTPUTS / "curve_scenarios.png", dpi=150)


def plot_surplus_results(base_curve: ZeroCurve, bonds: list[Bond], liabilities) -> None:
    """Plot surplus, asset value and liability value by scenario."""
    scenarios = get_stress_scenarios()
    stress_results = run_surplus_scenarios(bonds, liabilities, base_curve, scenarios)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#4C78A8" if value >= 0 else "#D55E00" for value in stress_results["surplus"]]
    ax.bar(stress_results["scenario"], stress_results["surplus"] / 1_000_000.0, color=colors)
    ax.axhline(0.0, color="black", linewidth=0.9)
    ax.set_title("Balance-Sheet Surplus by Scenario")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Surplus (millions)")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(True, axis="y", alpha=0.30)
    fig.tight_layout()
    fig.savefig(OUTPUTS / "surplus_by_scenario.png", dpi=150)

    fig2, ax2 = plt.subplots(figsize=(10, 6))
    x_positions = range(len(stress_results))
    width = 0.38
    ax2.bar(
        [x - width / 2 for x in x_positions],
        stress_results["asset_value"] / 1_000_000.0,
        width=width,
        label="Assets",
        color="#4C78A8",
    )
    ax2.bar(
        [x + width / 2 for x in x_positions],
        stress_results["liability_value"] / 1_000_000.0,
        width=width,
        label="Liabilities",
        color="#F58518",
    )
    ax2.set_title("Asset and Liability Values by Scenario")
    ax2.set_xlabel("Scenario")
    ax2.set_ylabel("Value (millions)")
    ax2.set_xticks(list(x_positions))
    ax2.set_xticklabels(stress_results["scenario"], rotation=30, ha="right")
    ax2.grid(True, axis="y", alpha=0.30)
    ax2.legend(frameon=False)
    fig2.tight_layout()
    fig2.savefig(OUTPUTS / "asset_liability_by_scenario.png", dpi=150)


def plot_cashflow_gap(cashflow_gap_report) -> None:
    """Plot annual asset, liability and net cash-flow gaps."""
    fig, ax = plt.subplots(figsize=(11, 6))
    x_positions = range(len(cashflow_gap_report))
    width = 0.28

    ax.bar(
        [x - width for x in x_positions],
        cashflow_gap_report["asset_cash_flow"] / 1_000_000.0,
        width=width,
        label="Assets",
        color="#4C78A8",
    )
    ax.bar(
        x_positions,
        cashflow_gap_report["liability_cash_flow"] / 1_000_000.0,
        width=width,
        label="Liabilities",
        color="#F58518",
    )
    ax.bar(
        [x + width for x in x_positions],
        cashflow_gap_report["net_cash_flow"] / 1_000_000.0,
        width=width,
        label="Net",
        color="#54A24B",
    )
    ax.axhline(0.0, color="black", linewidth=0.9)
    ax.set_title("Annual Asset/Liability Cash-Flow Gap")
    ax.set_xlabel("Bucket end year")
    ax.set_ylabel("Cash flow (millions)")
    ax.set_xticks(list(x_positions)[::2])
    ax.set_xticklabels(cashflow_gap_report["bucket_end"].iloc[::2].astype(int))
    ax.grid(True, axis="y", alpha=0.30)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUTPUTS / "cashflow_gap.png", dpi=150)


def plot_key_rate_pv01(key_rate_report) -> None:
    """Plot asset, liability and surplus key-rate PV01 by maturity."""
    fig, ax = plt.subplots(figsize=(10, 6))
    x_positions = range(len(key_rate_report))
    width = 0.26

    ax.bar(
        [x - width for x in x_positions],
        key_rate_report["asset_pv01"],
        width=width,
        label="Asset PV01",
        color="#4C78A8",
    )
    ax.bar(
        x_positions,
        key_rate_report["liability_pv01"],
        width=width,
        label="Liability PV01",
        color="#F58518",
    )
    ax.bar(
        [x + width for x in x_positions],
        key_rate_report["surplus_pv01"],
        width=width,
        label="Surplus PV01",
        color="#54A24B",
    )
    ax.axhline(0.0, color="black", linewidth=0.9)
    ax.set_title("Key-Rate PV01 by Maturity Bucket")
    ax.set_xlabel("Key maturity (years)")
    ax.set_ylabel("PV change for +1 bp")
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(key_rate_report["key_maturity"].map(lambda value: f"{value:g}"))
    ax.grid(True, axis="y", alpha=0.30)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUTPUTS / "key_rate_pv01.png", dpi=150)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot ALM curve and surplus results.")
    add_input_arguments(parser)
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display plots interactively after saving them.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    base_curve = load_curve(args.curve_csv)
    bonds = load_bonds(args.bonds_csv)
    liabilities = load_liabilities(args.liabilities_csv)
    asset_cash_flows = collect_asset_cash_flows(bonds)
    key_rate_report = compute_asset_liability_key_rate_report(
        asset_cash_flows,
        liabilities,
        base_curve,
        key_maturities=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
        width=2.0,
    )
    cashflow_gap_report = build_cashflow_gap_report(
        asset_cash_flows,
        liabilities,
        bucket_size=1.0,
        horizon=30.0,
    )

    plot_curve_scenarios(base_curve)
    plot_surplus_results(base_curve, bonds, liabilities)
    plot_cashflow_gap(cashflow_gap_report)
    plot_key_rate_pv01(key_rate_report)

    print(f"Saved plots to: {OUTPUTS}")
    if args.show:
        plt.show()
    else:
        plt.close("all")


if __name__ == "__main__":
    main()
