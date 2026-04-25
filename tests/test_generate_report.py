import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond
from yield_curve_alm_engine.scripts.generate_report import (
    build_report_markdown,
    build_report_tables,
    parse_args,
)


def test_generate_report_parse_args_accepts_output() -> None:
    args = parse_args(["--output", "outputs/custom_report.md"])

    assert str(args.output) == "outputs/custom_report.md"


def test_build_report_tables_and_markdown() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0, 10.0], zero_rates=[0.02, 0.025, 0.03])
    bonds = [
        Bond(
            name="Test Bond",
            face_value=100.0,
            coupon_rate=0.03,
            maturity_years=5.0,
            coupon_frequency=1,
        )
    ]
    liabilities = pd.DataFrame({"time_years": [1.0, 5.0], "cash_flow": [20.0, 70.0]})

    tables = build_report_tables(curve, bonds, liabilities)
    markdown = build_report_markdown(tables, input_note="Synthetic test inputs.")

    assert {"summary", "curve_analytics", "stress_results", "shock_comparison"}.issubset(tables)
    assert "# ALM Report" in markdown
    assert "## Executive Summary" in markdown
    assert "## Curve Diagnostics" in markdown
    assert "## Duration Approximation vs Full Revaluation" in markdown
    assert "## Key-Rate PV01" in markdown
    assert "## Cash-Flow Gap" in markdown
    assert "forward_5y_10y" in markdown
    assert "Largest absolute surplus PV01" in markdown
    assert "Worst surplus stress" in markdown
    assert "not a production market-data stack" in markdown
