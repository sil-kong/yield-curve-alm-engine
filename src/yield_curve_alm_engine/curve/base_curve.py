"""Zero-coupon yield curve representation.

The project uses continuously compounded zero rates:

    DF(t) = exp(-r(t) * t)

Rates between quoted maturities are obtained by linear interpolation. Rates
outside the quoted range use flat extrapolation at the nearest endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ZeroCurve:
    """A simple continuously compounded zero-coupon curve."""

    maturities: Iterable[float]
    zero_rates: Iterable[float]
    name: str = "base"

    def __post_init__(self) -> None:
        maturities = np.asarray(list(self.maturities), dtype=float)
        zero_rates = np.asarray(list(self.zero_rates), dtype=float)

        if maturities.ndim != 1 or zero_rates.ndim != 1:
            raise ValueError("maturities and zero_rates must be one-dimensional.")
        if len(maturities) != len(zero_rates):
            raise ValueError("maturities and zero_rates must have the same length.")
        if len(maturities) < 2:
            raise ValueError("a curve requires at least two maturity points.")
        if np.any(maturities <= 0):
            raise ValueError("all curve maturities must be strictly positive.")
        if np.any(np.diff(maturities) <= 0):
            raise ValueError("curve maturities must be strictly increasing.")

        object.__setattr__(self, "maturities", maturities)
        object.__setattr__(self, "zero_rates", zero_rates)

    def get_zero_rate(self, maturity: float) -> float:
        """Return the interpolated zero rate for a maturity in years."""
        return float(
            np.interp(
                maturity,
                self.maturities,
                self.zero_rates,
                left=self.zero_rates[0],
                right=self.zero_rates[-1],
            )
        )

    def get_zero_rates(self, maturities: Iterable[float]) -> np.ndarray:
        """Return interpolated zero rates for several maturities."""
        maturity_array = np.asarray(list(maturities), dtype=float)
        return np.interp(
            maturity_array,
            self.maturities,
            self.zero_rates,
            left=self.zero_rates[0],
            right=self.zero_rates[-1],
        )

    def get_discount_factor(self, maturity: float) -> float:
        """Return DF(t) under continuous compounding."""
        zero_rate = self.get_zero_rate(maturity)
        return float(np.exp(-zero_rate * maturity))

    def get_discount_factors(self, maturities: Iterable[float]) -> np.ndarray:
        """Return discount factors for several maturities."""
        maturity_array = np.asarray(list(maturities), dtype=float)
        zero_rates = self.get_zero_rates(maturity_array)
        return np.exp(-zero_rates * maturity_array)

    def with_zero_rates(self, zero_rates: Iterable[float], name: str) -> "ZeroCurve":
        """Create a new curve with the same maturities and supplied rates."""
        return ZeroCurve(maturities=self.maturities, zero_rates=zero_rates, name=name)

    def to_frame(self) -> pd.DataFrame:
        """Export quoted curve points and discount factors to a DataFrame."""
        return pd.DataFrame(
            {
                "curve": self.name,
                "maturity_years": self.maturities,
                "zero_rate": self.zero_rates,
                "discount_factor": self.get_discount_factors(self.maturities),
            }
        )


def create_base_zero_curve() -> ZeroCurve:
    """Create the synthetic base zero curve used by the examples."""
    maturities = [0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30]
    zero_rates = [0.020, 0.021, 0.022, 0.023, 0.025, 0.026, 0.027, 0.028, 0.029, 0.030]
    return ZeroCurve(maturities=maturities, zero_rates=zero_rates, name="base")
