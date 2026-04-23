import numpy as np
import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve


def test_zero_curve_interpolates_and_flat_extrapolates() -> None:
    curve = ZeroCurve(maturities=[1.0, 3.0], zero_rates=[0.02, 0.04])

    assert curve.get_zero_rate(2.0) == pytest.approx(0.03)
    assert curve.get_zero_rate(0.5) == pytest.approx(0.02)
    assert curve.get_zero_rate(5.0) == pytest.approx(0.04)


def test_discount_factor_uses_continuous_compounding() -> None:
    curve = ZeroCurve(maturities=[1.0, 3.0], zero_rates=[0.02, 0.04])

    assert curve.get_discount_factor(2.0) == pytest.approx(np.exp(-0.03 * 2.0))
