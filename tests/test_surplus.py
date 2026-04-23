import numpy as np
import pandas as pd
import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond
from yield_curve_alm_engine.risk.surplus import compute_balance_sheet


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
