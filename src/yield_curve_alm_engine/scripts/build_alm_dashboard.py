"""Build a compact ALM dashboard from the stylized base case."""

from __future__ import annotations

import argparse

import pandas as pd

from yield_curve_alm_engine.config import OUTPUTS
from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond, price_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import (
    create_stylized_liability_schedule,
    liability_risk_metrics,
)
from yield_curve_alm_engine.risk.cashflow_matching import build_cashflow_gap_report
from yield_curve_alm_engine.risk.immunization import (
    compute_duration_gap,
    estimate_parallel_surplus_impact,
)
from yield_curve_alm_engine.risk.key_rate import compute_asset_liability_key_rate_report
from yield_curve_alm_engine.risk.surplus import compute_balance_sheet
from yield_curve_alm_engine.scripts.common import add_input_arguments, load_bonds, load_curve


def _currency(value: float) -> str:
    return f"{value:,.0f}"


def _weighted_metric(table: pd.DataFrame, metric: str) -> float:
    weights = table["price"] / table["price"].sum()
    return float((weights * table[metric]).sum())


def _asset_cash_flows(bonds: list[Bond]) -> pd.DataFrame:
    frames = [bond.cash_flows().loc[:, ["time_years", "cash_flow"]] for bond in bonds]
    return pd.concat(frames, ignore_index=True)


def build_dashboard_tables(
    curve: ZeroCurve,
    bonds: list[Bond],
    liabilities: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build dashboard summary, key-rate and cash-flow gap tables."""
    bond_table = price_bond_portfolio(bonds, curve)
    liability_metrics = liability_risk_metrics(liabilities, curve)
    balance_sheet = compute_balance_sheet(bonds, liabilities, curve, scenario="base")
    asset_cash_flows = _asset_cash_flows(bonds)

    asset_modified_duration = _weighted_metric(bond_table, "modified_duration")
    liability_modified_duration = liability_metrics["modified_duration"]
    duration_gap = compute_duration_gap(
        asset_value=float(balance_sheet["asset_value"]),
        liability_value=float(balance_sheet["liability_value"]),
        asset_duration=asset_modified_duration,
        liability_duration=liability_modified_duration,
    )
    estimated_surplus_change_1bp = estimate_parallel_surplus_impact(
        asset_value=float(balance_sheet["asset_value"]),
        liability_value=float(balance_sheet["liability_value"]),
        asset_duration=asset_modified_duration,
        liability_duration=liability_modified_duration,
        shock_size=0.0001,
    )

    summary = pd.DataFrame(
        [
            {
                "metric": "asset_market_value",
                "value": float(balance_sheet["asset_value"]),
                "unit": "currency",
                "interpretation": "Market value of the stylized fixed-rate bond portfolio.",
            },
            {
                "metric": "liability_present_value",
                "value": float(balance_sheet["liability_value"]),
                "unit": "currency",
                "interpretation": "Present value of positive synthetic liability outflows.",
            },
            {
                "metric": "surplus",
                "value": float(balance_sheet["surplus"]),
                "unit": "currency",
                "interpretation": "Asset market value minus liability present value.",
            },
            {
                "metric": "asset_modified_duration",
                "value": asset_modified_duration,
                "unit": "years",
                "interpretation": "Market-value weighted modified duration of assets.",
            },
            {
                "metric": "liability_modified_duration",
                "value": liability_modified_duration,
                "unit": "years",
                "interpretation": "Modified duration of the liability cash-flow stream.",
            },
            {
                "metric": "duration_gap",
                "value": duration_gap,
                "unit": "years",
                "interpretation": "Asset duration minus funded liability duration.",
            },
            {
                "metric": "asset_convexity",
                "value": _weighted_metric(bond_table, "convexity"),
                "unit": "years_squared",
                "interpretation": "Market-value weighted convexity of assets.",
            },
            {
                "metric": "liability_convexity",
                "value": liability_metrics["convexity"],
                "unit": "years_squared",
                "interpretation": "Convexity of the liability cash-flow stream.",
            },
            {
                "metric": "estimated_surplus_change_1bp_up",
                "value": estimated_surplus_change_1bp,
                "unit": "currency",
                "interpretation": "First-order surplus impact estimate for a +1 bp parallel rate shock.",
            },
        ]
    )

    key_rate_report = compute_asset_liability_key_rate_report(
        asset_cash_flows=asset_cash_flows,
        liability_cash_flows=liabilities,
        curve=curve,
        key_maturities=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
        width=2.0,
    )
    cashflow_gap_report = build_cashflow_gap_report(
        asset_cash_flows=asset_cash_flows,
        liability_cash_flows=liabilities,
        bucket_size=1.0,
        horizon=30.0,
    )

    return {
        "summary": summary,
        "key_rate_report": key_rate_report,
        "cashflow_gap_report": cashflow_gap_report,
    }


def _summary_value(summary: pd.DataFrame, metric: str) -> float:
    return float(summary.loc[summary["metric"] == metric, "value"].iloc[0])


def build_dashboard_markdown(summary: pd.DataFrame) -> str:
    """Build a short Markdown dashboard narrative."""
    metric_table = summary.copy()
    metric_table["value"] = metric_table["value"].map(lambda value: f"{value:,.4f}")
    table_lines = [
        "| metric | value | unit | interpretation |",
        "| --- | ---: | --- | --- |",
    ]
    for row in metric_table.itertuples(index=False):
        table_lines.append(
            f"| {row.metric} | {row.value} | {row.unit} | {row.interpretation} |"
        )

    return "\n".join(
        [
            "# ALM Dashboard",
            "",
            "This dashboard is generated from synthetic curve, bond and liability inputs.",
            "It is intended for transparent ALM mechanics, not production reporting.",
            "",
            "## Base Case",
            "",
            f"- Asset market value: {_currency(_summary_value(summary, 'asset_market_value'))}",
            f"- Liability present value: {_currency(_summary_value(summary, 'liability_present_value'))}",
            f"- Surplus: {_currency(_summary_value(summary, 'surplus'))}",
            f"- Duration gap: {_summary_value(summary, 'duration_gap'):,.2f} years",
            f"- Estimated surplus change for +1 bp: {_currency(_summary_value(summary, 'estimated_surplus_change_1bp_up'))}",
            "",
            "## Metrics",
            "",
            *table_lines,
            "",
            "## Interpretation",
            "",
            "The summary links balance-sheet surplus to duration and convexity diagnostics. "
            "The key-rate report decomposes local rate sensitivity by maturity bucket, while "
            "the cash-flow gap report compares annual asset and liability cash-flow timing.",
            "",
            "## Limitations",
            "",
            "All inputs are synthetic. The report does not include market curve bootstrapping, "
            "credit risk, stochastic rates, actuarial modelling, accounting rules or regulatory capital.",
            "",
            "## Output Files",
            "",
            "- `outputs/alm_dashboard_summary.csv`",
            "- `outputs/key_rate_report.csv`",
            "- `outputs/cashflow_gap_report.csv`",
            "- `outputs/alm_dashboard.md`",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ALM dashboard outputs.")
    add_input_arguments(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    curve = load_curve(args.curve_csv)
    bonds = load_bonds(args.bonds_csv)
    liabilities = create_stylized_liability_schedule()

    tables = build_dashboard_tables(curve, bonds, liabilities)
    markdown = build_dashboard_markdown(tables["summary"])

    tables["summary"].to_csv(OUTPUTS / "alm_dashboard_summary.csv", index=False)
    tables["key_rate_report"].to_csv(OUTPUTS / "key_rate_report.csv", index=False)
    tables["cashflow_gap_report"].to_csv(OUTPUTS / "cashflow_gap_report.csv", index=False)
    (OUTPUTS / "alm_dashboard.md").write_text(markdown)

    print("\nALM Dashboard")
    print("-------------")
    print(f"Summary metrics saved to : {OUTPUTS / 'alm_dashboard_summary.csv'}")
    print(f"Key-rate report saved to : {OUTPUTS / 'key_rate_report.csv'}")
    print(f"Cash-flow gap saved to   : {OUTPUTS / 'cashflow_gap_report.csv'}")
    print(f"Markdown report saved to : {OUTPUTS / 'alm_dashboard.md'}")


if __name__ == "__main__":
    main()
