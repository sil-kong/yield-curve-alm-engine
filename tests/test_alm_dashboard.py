import pandas as pd

import yield_curve_alm_engine.scripts.build_alm_dashboard as dashboard
from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond


def test_build_alm_dashboard_module_imports() -> None:
    assert dashboard.main is not None


def test_build_dashboard_tables_returns_expected_outputs() -> None:
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

    tables = dashboard.build_dashboard_tables(curve, bonds, liabilities)

    assert set(tables) == {"summary", "key_rate_report", "cashflow_gap_report"}
    assert list(tables["summary"].columns) == ["metric", "value", "unit", "interpretation"]
    assert "surplus" in set(tables["summary"]["metric"])
    assert {"asset_pv01", "liability_pv01", "surplus_pv01"}.issubset(
        tables["key_rate_report"].columns
    )
