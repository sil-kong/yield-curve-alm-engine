import numpy as np
import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.curve.shocks import parallel_up_100bps
from yield_curve_alm_engine.instruments.bonds import Bond, price_bond


def test_zero_coupon_bond_price_matches_discounted_principal() -> None:
    curve = ZeroCurve(maturities=[1.0, 2.0], zero_rates=[0.05, 0.05])
    bond = Bond(
        name="Test Zero Coupon",
        face_value=100.0,
        coupon_rate=0.0,
        maturity_years=1.0,
        coupon_frequency=1,
    )

    assert price_bond(bond, curve) == pytest.approx(100.0 * np.exp(-0.05))


def test_parallel_rate_increase_lowers_standard_bond_price() -> None:
    base_curve = ZeroCurve(maturities=[1.0, 3.0], zero_rates=[0.02, 0.02])
    shocked_curve = parallel_up_100bps(base_curve)
    bond = Bond(
        name="Test Coupon Bond",
        face_value=100.0,
        coupon_rate=0.05,
        maturity_years=3.0,
        coupon_frequency=1,
    )

    assert price_bond(bond, shocked_curve) < price_bond(bond, base_curve)
