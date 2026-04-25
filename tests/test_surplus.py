import numpy as np
import pandas as pd
import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond
from yield_curve_alm_engine.risk.surplus import (
    compute_balance_sheet,
    parallel_surplus_shock_comparison,
)


def test_balance_sheet_surplus_is_assets_minus_liabilities() -> None:
    curve = ZeroCurve(maturities=[1.0, 2.0], zero_rates=[0.02, 0.02])
    bonds = [
        Bond(
            name="Test Asset",
            face_value=100.0,
            coupon_rate=0.0,
            maturity_years=1.0,
            coupon_frequency=1,
        )
    ]
    liabilities = pd.DataFrame({"time_years": [1.0], "cash_flow": [50.0]})

    result = compute_balance_sheet(bonds, liabilities, curve)
    expected_surplus = 50.0 * np.exp(-0.02)

    assert result["asset_value"] == pytest.approx(100.0 * np.exp(-0.02))
    assert result["liability_value"] == pytest.approx(50.0 * np.exp(-0.02))
    assert result["surplus"] == pytest.approx(expected_surplus)


def test_parallel_surplus_shock_comparison_reports_exact_and_estimated_changes() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0], zero_rates=[0.02, 0.025])
    bonds = [
        Bond(
            name="Test Bond",
            face_value=100.0,
            coupon_rate=0.03,
            maturity_years=5.0,
            coupon_frequency=1,
        )
    ]
    liabilities = pd.DataFrame({"time_years": [5.0], "cash_flow": [90.0]})

    comparison = parallel_surplus_shock_comparison(
        bonds=bonds,
        liabilities=liabilities,
        curve=curve,
        shock_size=0.0001,
    )

    assert comparison["parallel_shock_bps"] == pytest.approx(1.0)
    assert comparison["shocked_asset_value"] < comparison["base_asset_value"]
    assert comparison["shocked_liability_value"] < comparison["base_liability_value"]
    assert "estimate_error" in comparison
