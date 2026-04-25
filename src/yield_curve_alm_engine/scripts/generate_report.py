"""Generate a professional-style Markdown ALM report."""

from __future__ import annotations

import argparse
import numbers
from pathlib import Path

import numpy as np
import pandas as pd

from yield_curve_alm_engine.config import OUTPUTS
from yield_curve_alm_engine.curve.analytics import compute_curve_analytics
from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.curve.shocks import get_stress_scenarios
from yield_curve_alm_engine.instruments.bonds import Bond
from yield_curve_alm_engine.risk.surplus import (
    parallel_surplus_shock_comparisons,
    run_surplus_scenarios,
)
from yield_curve_alm_engine.scripts.build_alm_dashboard import build_dashboard_tables
from yield_curve_alm_engine.scripts.common import (
    add_input_arguments,
    load_bonds,
    load_curve,
    load_liabilities,
)


def _format_number(value: float) -> str:
    if not np.isfinite(value):
        return "n/a"
    if abs(value) >= 1_000:
        return f"{value:,.0f}"
    return f"{value:,.6f}".rstrip("0").rstrip(".")


def _format_value(value: object) -> str:
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        return _format_number(float(value))
    return str(value)


def _markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    table = frame.loc[:, columns].copy() if columns else frame.copy()
    header = "| " + " | ".join(table.columns) + " |"
    separator = "| " + " | ".join("---" for _ in table.columns) + " |"
    rows = []
    for row in table.itertuples(index=False):
        rows.append("| " + " | ".join(_format_value(value) for value in row) + " |")
    return "\n".join([header, separator, *rows])


def _metric_value(table: pd.DataFrame, metric: str) -> float:
    matches = table.loc[table["metric"] == metric, "value"]
    if matches.empty:
        raise ValueError(f"metric not found in report table: {metric}")
    return float(matches.iloc[0])


def _select_metrics(table: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = []
    for metric in metrics:
        match = table.loc[table["metric"] == metric]
        if not match.empty:
            rows.append(match.iloc[0])
    if not rows:
        return pd.DataFrame(columns=table.columns)
    return pd.DataFrame(rows).reset_index(drop=True)


def build_report_tables(
    curve: ZeroCurve,
    bonds: list[Bond],
    liabilities: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build the tables used by the Markdown report."""
    dashboard_tables = build_dashboard_tables(curve, bonds, liabilities)
    stress_results = run_surplus_scenarios(
        bonds=bonds,
        liabilities=liabilities,
        base_curve=curve,
        scenarios=get_stress_scenarios(),
        include_base=True,
    )
    shock_comparison = parallel_surplus_shock_comparisons(
        bonds=bonds,
        liabilities=liabilities,
        curve=curve,
        shock_sizes=(0.0001, 0.01, -0.01),
    )

    return {
        "summary": dashboard_tables["summary"],
        "curve_analytics": compute_curve_analytics(curve),
        "key_rate_report": dashboard_tables["key_rate_report"],
        "cashflow_gap_report": dashboard_tables["cashflow_gap_report"],
        "stress_results": stress_results,
        "shock_comparison": shock_comparison,
    }


def _stress_extremes(stress_results: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    scenario_rows = stress_results[stress_results["scenario"] != "base"]
    if scenario_rows.empty:
        scenario_rows = stress_results
    worst = scenario_rows.loc[scenario_rows["surplus_change"].idxmin()]
    best = scenario_rows.loc[scenario_rows["surplus_change"].idxmax()]
    return worst, best


def _largest_key_rate_row(key_rate_report: pd.DataFrame) -> pd.Series:
    return key_rate_report.loc[key_rate_report["surplus_pv01"].abs().idxmax()]


def _largest_cashflow_gap_row(cashflow_gap_report: pd.DataFrame) -> pd.Series:
    return cashflow_gap_report.loc[cashflow_gap_report["net_cash_flow"].abs().idxmax()]


def _curve_slope_interpretation(slope_2y_10y: float) -> str:
    if slope_2y_10y > 0.0001:
        return "The curve is upward-sloping between 2Y and 10Y."
    if slope_2y_10y < -0.0001:
        return "The curve is inverted between 2Y and 10Y."
    return "The curve is relatively flat between 2Y and 10Y."


def _duration_gap_interpretation(duration_gap: float) -> str:
    if duration_gap < -0.05:
        return (
            "The funded liability duration exceeds asset duration, so first-order "
            "surplus sensitivity tends to benefit from higher rates and suffer from lower rates."
        )
    if duration_gap > 0.05:
        return (
            "Asset duration exceeds funded liability duration, so first-order surplus "
            "sensitivity tends to suffer from higher rates and benefit from lower rates."
        )
    return "The duration gap is close to neutral in this simplified first-order view."


def _cashflow_gap_bucket_label(row: pd.Series) -> str:
    return f"{float(row['bucket_start']):g}-{float(row['bucket_end']):g}Y"


def _build_interpretation_bullets(
    summary: pd.DataFrame,
    curve_analytics: pd.DataFrame,
    stress_results: pd.DataFrame,
    key_rate_report: pd.DataFrame,
    cashflow_gap_report: pd.DataFrame,
    shock_comparison: pd.DataFrame,
) -> list[str]:
    surplus = _metric_value(summary, "surplus")
    asset_duration = _metric_value(summary, "asset_modified_duration")
    liability_duration = _metric_value(summary, "liability_modified_duration")
    duration_gap = _metric_value(summary, "duration_gap")
    slope_2y_10y = _metric_value(curve_analytics, "slope_2y_10y")
    worst_stress, best_stress = _stress_extremes(stress_results)
    key_rate_row = _largest_key_rate_row(key_rate_report)
    cashflow_gap_row = _largest_cashflow_gap_row(cashflow_gap_report)
    final_cumulative_gap = float(cashflow_gap_report["cumulative_net_cash_flow"].iloc[-1])

    shock_100 = shock_comparison[
        shock_comparison["parallel_shock_bps"].round(8) == 100.0
    ].iloc[0]
    materiality = abs(float(shock_100["estimate_error"]))
    exact_100 = abs(float(shock_100["exact_surplus_change"]))
    approximation_text = "is small"
    if exact_100 > 0 and materiality / exact_100 > 0.05:
        approximation_text = "is visible"

    surplus_text = "positive" if surplus >= 0 else "negative"
    longer_duration_text = (
        "assets have longer modified duration than liabilities"
        if asset_duration > liability_duration
        else "liabilities have longer modified duration than assets"
    )

    return [
        f"Base surplus is {surplus_text} at {_format_number(surplus)}.",
        f"In unscaled terms, {longer_duration_text}.",
        _duration_gap_interpretation(duration_gap),
        _curve_slope_interpretation(slope_2y_10y),
        (
            f"The most adverse deterministic stress is `{worst_stress['scenario']}` "
            f"with surplus change {_format_number(float(worst_stress['surplus_change']))}."
        ),
        (
            f"The most favorable deterministic stress is `{best_stress['scenario']}` "
            f"with surplus change {_format_number(float(best_stress['surplus_change']))}."
        ),
        (
            f"Largest absolute surplus PV01 is around "
            f"{_format_number(float(key_rate_row['key_maturity']))}Y."
        ),
        (
            f"The largest annual cash-flow mismatch occurs in the "
            f"{_cashflow_gap_bucket_label(cashflow_gap_row)} bucket."
        ),
        (
            f"The final cumulative net cash-flow gap is "
            f"{_format_number(final_cumulative_gap)}."
        ),
        (
            f"For a +100 bps parallel shock, duration approximation error "
            f"{approximation_text} relative to full revaluation."
        ),
    ]


def build_report_markdown(
    tables: dict[str, pd.DataFrame],
    input_note: str,
) -> str:
    """Build a Markdown ALM report from precomputed ALM tables."""
    summary = tables["summary"]
    curve_analytics = tables["curve_analytics"]
    stress_results = tables["stress_results"]
    key_rate_report = tables["key_rate_report"]
    cashflow_gap_report = tables["cashflow_gap_report"]
    shock_comparison = tables["shock_comparison"]

    worst_stress, best_stress = _stress_extremes(stress_results)
    key_rate_row = _largest_key_rate_row(key_rate_report)
    cashflow_gap_row = _largest_cashflow_gap_row(cashflow_gap_report)

    executive_summary = pd.DataFrame(
        [
            {
                "metric": "asset_market_value",
                "value": _metric_value(summary, "asset_market_value"),
                "unit": "currency",
            },
            {
                "metric": "liability_present_value",
                "value": _metric_value(summary, "liability_present_value"),
                "unit": "currency",
            },
            {"metric": "surplus", "value": _metric_value(summary, "surplus"), "unit": "currency"},
            {
                "metric": "asset_modified_duration",
                "value": _metric_value(summary, "asset_modified_duration"),
                "unit": "years",
            },
            {
                "metric": "liability_modified_duration",
                "value": _metric_value(summary, "liability_modified_duration"),
                "unit": "years",
            },
            {
                "metric": "duration_gap",
                "value": _metric_value(summary, "duration_gap"),
                "unit": "years",
            },
            {
                "metric": "slope_2y_10y",
                "value": _metric_value(curve_analytics, "slope_2y_10y"),
                "unit": "decimal_rate",
            },
            {
                "metric": "curvature_2y_5y_10y",
                "value": _metric_value(curve_analytics, "curvature_2y_5y_10y"),
                "unit": "decimal_rate",
            },
            {
                "metric": "forward_5y_10y",
                "value": _metric_value(curve_analytics, "forward_5y_10y"),
                "unit": "decimal_rate",
            },
            {
                "metric": "worst_surplus_stress",
                "value": worst_stress["scenario"],
                "unit": "scenario",
            },
            {
                "metric": "largest_abs_surplus_pv01_maturity",
                "value": float(key_rate_row["key_maturity"]),
                "unit": "years",
            },
            {
                "metric": "largest_cashflow_mismatch_bucket",
                "value": _cashflow_gap_bucket_label(cashflow_gap_row),
                "unit": "years",
            },
        ]
    )

    curve_rows = _select_metrics(
        curve_analytics,
        [
            "zero_rate_1y",
            "zero_rate_5y",
            "zero_rate_10y",
            "zero_rate_30y",
            "slope_2y_10y",
            "curvature_2y_5y_10y",
            "forward_1y_5y",
            "forward_5y_10y",
            "forward_10y_30y",
            "discount_factor_10y",
            "discount_factor_30y",
        ],
    )
    base_rows = _select_metrics(
        summary,
        [
            "asset_market_value",
            "liability_present_value",
            "surplus",
            "asset_modified_duration",
            "liability_modified_duration",
            "duration_gap",
            "asset_convexity",
            "liability_convexity",
        ],
    )
    shock_rows = shock_comparison.loc[
        :,
        [
            "parallel_shock_bps",
            "exact_surplus_change",
            "estimated_surplus_change",
            "estimate_error",
            "relative_error_vs_exact",
        ],
    ]
    stress_rows = stress_results.loc[
        :,
        [
            "scenario",
            "asset_value",
            "liability_value",
            "surplus",
            "surplus_change",
            "surplus_change_pct",
        ],
    ]
    key_rate_rows = (
        key_rate_report.assign(abs_surplus_pv01=key_rate_report["surplus_pv01"].abs())
        .sort_values("abs_surplus_pv01", ascending=False)
        .head(5)
        .loc[:, ["key_maturity", "asset_pv01", "liability_pv01", "surplus_pv01"]]
    )
    cashflow_rows = (
        cashflow_gap_report.assign(abs_net_cash_flow=cashflow_gap_report["net_cash_flow"].abs())
        .sort_values("abs_net_cash_flow", ascending=False)
        .head(5)
        .loc[
            :,
            [
                "bucket_start",
                "bucket_end",
                "asset_cash_flow",
                "liability_cash_flow",
                "net_cash_flow",
                "cumulative_net_cash_flow",
            ],
        ]
    )
    interpretation_bullets = _build_interpretation_bullets(
        summary=summary,
        curve_analytics=curve_analytics,
        stress_results=stress_results,
        key_rate_report=key_rate_report,
        cashflow_gap_report=cashflow_gap_report,
        shock_comparison=shock_comparison,
    )

    return "\n".join(
        [
            "# ALM Report",
            "",
            "This report is generated by a fixed-income ALM analytics prototype.",
            "It converts public/local yield curves and local cash-flow inputs into reproducible valuation, sensitivity and surplus diagnostics.",
            "",
            "## Executive Summary",
            "",
            _markdown_table(executive_summary),
            "",
            "## Input Scope",
            "",
            input_note,
            "",
            "## Curve Diagnostics",
            "",
            _markdown_table(curve_rows, ["metric", "value", "unit"]),
            "",
            _curve_slope_interpretation(_metric_value(curve_analytics, "slope_2y_10y")),
            "",
            "## Base Balance Sheet",
            "",
            _markdown_table(base_rows, ["metric", "value", "unit"]),
            "",
            "## Duration Approximation vs Full Revaluation",
            "",
            "The table compares full revaluation with a first-order duration estimate. Duration is a local approximation; larger shocks require full revaluation.",
            "",
            _markdown_table(shock_rows),
            "",
            "## Stress Test Results",
            "",
            _markdown_table(stress_rows),
            "",
            f"Worst surplus stress: `{worst_stress['scenario']}`. Best surplus stress: `{best_stress['scenario']}`.",
            "",
            "## Key-Rate PV01",
            "",
            _markdown_table(key_rate_rows),
            "",
            (
                "Largest absolute surplus PV01 is around "
                f"{_format_number(float(key_rate_row['key_maturity']))} years."
            ),
            "",
            "## Cash-Flow Gap",
            "",
            _markdown_table(cashflow_rows),
            "",
            (
                "Largest absolute net cash-flow gap occurs in the "
                f"{_cashflow_gap_bucket_label(cashflow_gap_row)} bucket. "
                f"Final cumulative net gap is "
                f"{_format_number(float(cashflow_gap_report['cumulative_net_cash_flow'].iloc[-1]))}."
            ),
            "",
            "## Interpretation",
            "",
            *[f"- {bullet}" for bullet in interpretation_bullets],
            "",
            "## Limitations",
            "",
            "- Fixed-rate bullet bonds are simplified and accrued-free.",
            "- Day-count conventions, settlement calendars and accrued interest are not modelled yet.",
            "- There is no credit spread curve, default model or liquidity premium layer yet.",
            "- Liability inputs are cash-flow schedules, not actuarial projection models.",
            "- ECB curve ingestion is public-data ingestion, not a production market-data stack.",
            "- Rate stresses are deterministic; there is no PCA or stochastic curve model yet.",
            "",
            "## Related Outputs",
            "",
            "- `outputs/alm_dashboard_summary.csv`",
            "- `outputs/base_case_shock_comparison.csv`",
            "- `outputs/key_rate_report.csv`",
            "- `outputs/cashflow_gap_report.csv`",
            "- `outputs/stress_test_results.csv`",
            "- `outputs/curve_scenarios.png`",
            "- `outputs/surplus_by_scenario.png`",
            "- `outputs/key_rate_pv01.png`",
            "- `outputs/cashflow_gap.png`",
            "",
        ]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Markdown ALM report.")
    add_input_arguments(parser)
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUTS / "alm_report.md",
        help="Markdown output path. Defaults to outputs/alm_report.md.",
    )
    return parser.parse_args(argv)


def _input_note(args: argparse.Namespace) -> str:
    if args.curve_csv and "ecb" in str(args.curve_csv).lower():
        return (
            "The report uses an ECB/public yield-curve CSV plus local asset and "
            "liability cash-flow inputs. Valuation and reporting run offline from "
            "those local files."
        )
    if args.curve_csv or args.bonds_csv or args.liabilities_csv:
        return (
            "The report uses local CSV inputs where supplied. The valuation step "
            "runs offline from those files; live internet is only used by the "
            "separate ECB fetch command when refreshing curve CSVs."
        )
    return (
        "The report uses the built-in synthetic fallback curve, bond portfolio "
        "and liability schedule provided for reproducible examples."
    )


def main() -> None:
    args = parse_args()
    curve = load_curve(args.curve_csv)
    bonds = load_bonds(args.bonds_csv)
    liabilities = load_liabilities(args.liabilities_csv)

    tables = build_report_tables(curve, bonds, liabilities)
    markdown = build_report_markdown(tables, input_note=_input_note(args))

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown)

    tables["curve_analytics"].to_csv(OUTPUTS / "report_curve_analytics.csv", index=False)
    tables["shock_comparison"].to_csv(OUTPUTS / "report_shock_comparison.csv", index=False)

    print(f"Markdown ALM report saved to: {output_path}")
    print(f"Supporting report tables saved to: {OUTPUTS}")


if __name__ == "__main__":
    main()
