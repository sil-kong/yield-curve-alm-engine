import pandas as pd
import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.risk.key_rate import (
    apply_key_rate_shock,
    compute_asset_liability_key_rate_report,
    compute_key_rate_pv01,
)


def test_apply_key_rate_shock_modifies_curve_locally() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0, 10.0], zero_rates=[0.02, 0.025, 0.03])

    shocked = apply_key_rate_shock(curve, key_maturity=5.0, shock_size=0.0001, width=1.0)

    assert shocked.get_zero_rate(5.0) == pytest.approx(0.0251)
    assert shocked.get_zero_rate(1.0) == pytest.approx(0.02)
    assert shocked.get_zero_rate(10.0) == pytest.approx(0.03)


def test_key_rate_shock_falls_back_to_nearest_curve_point() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0, 10.0], zero_rates=[0.02, 0.025, 0.03])

    shocked = apply_key_rate_shock(curve, key_maturity=7.0, shock_size=0.0001, width=0.5)

    assert shocked.get_zero_rate(5.0) == pytest.approx(0.0251)
    assert shocked.get_zero_rate(10.0) == pytest.approx(0.03)


def test_positive_cash_flows_have_negative_pv01_when_rates_rise() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0, 10.0], zero_rates=[0.02, 0.025, 0.03])
    cash_flows = pd.DataFrame({"time_years": [5.0], "cash_flow": [100.0]})

    report = compute_key_rate_pv01(cash_flows, curve, key_maturities=[5.0])

    assert report.loc[0, "pv01"] < 0
    assert report.loc[0, "key_rate_duration"] > 0


def test_long_cash_flow_is_more_sensitive_to_long_bucket_than_short_cash_flow() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0, 10.0], zero_rates=[0.02, 0.025, 0.03])
    short_cash_flow = pd.DataFrame({"time_years": [1.0], "cash_flow": [100.0]})
    long_cash_flow = pd.DataFrame({"time_years": [10.0], "cash_flow": [100.0]})

    short_report = compute_key_rate_pv01(short_cash_flow, curve, key_maturities=[10.0])
    long_report = compute_key_rate_pv01(long_cash_flow, curve, key_maturities=[10.0])

    assert abs(long_report.loc[0, "pv01"]) > abs(short_report.loc[0, "pv01"])


def test_asset_liability_key_rate_report_has_expected_columns() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0, 10.0], zero_rates=[0.02, 0.025, 0.03])
    asset_cash_flows = pd.DataFrame({"time_years": [5.0], "cash_flow": [100.0]})
    liability_cash_flows = pd.DataFrame({"time_years": [10.0], "cash_flow": [80.0]})

    report = compute_asset_liability_key_rate_report(
        asset_cash_flows,
        liability_cash_flows,
        curve,
        key_maturities=[1.0, 5.0, 10.0],
    )

    assert set(report.columns) == {
        "key_maturity",
        "asset_pv01",
        "liability_pv01",
        "surplus_pv01",
        "asset_key_rate_duration",
        "liability_key_rate_duration",
        "key_rate_duration_gap",
    }
