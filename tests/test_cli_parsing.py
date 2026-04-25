from pathlib import Path

from yield_curve_alm_engine.scripts.build_base_case import parse_args as parse_base_args
from yield_curve_alm_engine.scripts.fetch_ecb_curve import parse_args as parse_fetch_args
from yield_curve_alm_engine.scripts.run_stress_tests import parse_args as parse_stress_args


def test_fetch_ecb_parse_args_handles_required_options() -> None:
    args = parse_fetch_args(
        [
            "--curve-type",
            "aaa",
            "--date",
            "latest",
            "--output",
            "data/market_curves/ecb/ecb_aaa_spot_latest.csv",
        ]
    )

    assert args.curve_type == "aaa"
    assert args.date == "latest"
    assert args.output == "data/market_curves/ecb/ecb_aaa_spot_latest.csv"


def test_build_base_parse_args_accepts_liabilities_csv() -> None:
    args = parse_base_args(
        [
            "--liabilities-csv",
            "data/examples/liabilities/example_liability_cashflows.csv",
        ]
    )

    assert args.liabilities_csv == Path("data/examples/liabilities/example_liability_cashflows.csv")


def test_run_stress_parse_args_accepts_liabilities_csv() -> None:
    args = parse_stress_args(
        [
            "--liabilities-csv",
            "data/examples/liabilities/example_liability_cashflows.csv",
        ]
    )

    assert args.liabilities_csv == Path("data/examples/liabilities/example_liability_cashflows.csv")
