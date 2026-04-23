import pandas as pd
import pytest

from yield_curve_alm_engine.risk.cashflow_matching import (
    bucket_cash_flows,
    build_cashflow_gap_report,
)


def test_bucket_cash_flows_uses_ceil_bucket_convention() -> None:
    cash_flows = pd.DataFrame(
        {
            "time_years": [0.5, 1.0, 1.5, 2.0],
            "cash_flow": [10.0, 20.0, 30.0, 40.0],
        }
    )

    bucketed = bucket_cash_flows(cash_flows, bucket_size=1.0, label="asset_cash_flow")

    assert bucketed.loc[0, "bucket_start"] == pytest.approx(0.0)
    assert bucketed.loc[0, "bucket_end"] == pytest.approx(1.0)
    assert bucketed.loc[0, "asset_cash_flow"] == pytest.approx(30.0)
    assert bucketed.loc[1, "asset_cash_flow"] == pytest.approx(70.0)


def test_cashflow_gap_report_has_annual_and_cumulative_gaps() -> None:
    asset_cash_flows = pd.DataFrame({"time_years": [1.0, 2.0], "cash_flow": [100.0, 50.0]})
    liability_cash_flows = pd.DataFrame({"time_years": [1.0, 2.0], "cash_flow": [80.0, 90.0]})

    report = build_cashflow_gap_report(asset_cash_flows, liability_cash_flows)

    assert list(report.columns) == [
        "bucket_start",
        "bucket_end",
        "asset_cash_flow",
        "liability_cash_flow",
        "net_cash_flow",
        "cumulative_asset_cash_flow",
        "cumulative_liability_cash_flow",
        "cumulative_net_cash_flow",
    ]
    assert report.loc[0, "net_cash_flow"] == pytest.approx(20.0)
    assert report.loc[1, "net_cash_flow"] == pytest.approx(-40.0)
    assert report.loc[1, "cumulative_net_cash_flow"] == pytest.approx(-20.0)


def test_cashflow_gap_report_extends_to_requested_horizon() -> None:
    asset_cash_flows = pd.DataFrame({"time_years": [1.0], "cash_flow": [100.0]})
    liability_cash_flows = pd.DataFrame({"time_years": [1.0], "cash_flow": [70.0]})

    report = build_cashflow_gap_report(asset_cash_flows, liability_cash_flows, horizon=3.0)

    assert len(report) == 3
    assert report.loc[2, "bucket_start"] == pytest.approx(2.0)
    assert report.loc[2, "asset_cash_flow"] == pytest.approx(0.0)
    assert report.loc[2, "cumulative_net_cash_flow"] == pytest.approx(30.0)
