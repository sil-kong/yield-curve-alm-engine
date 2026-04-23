"""Fixed-rate bond instruments and portfolio helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.risk.duration_convexity import (
    convexity,
    macaulay_duration,
    modified_duration,
    present_value_from_cash_flows,
)


@dataclass(frozen=True)
class Bond:
    """A stylized fixed-rate bullet bond priced from full cash flows."""

    name: str
    face_value: float
    coupon_rate: float
    maturity_years: float
    coupon_frequency: int = 1

    def __post_init__(self) -> None:
        if self.face_value <= 0:
            raise ValueError("face_value must be positive.")
        if self.coupon_rate < 0:
            raise ValueError("coupon_rate cannot be negative.")
        if self.maturity_years <= 0:
            raise ValueError("maturity_years must be positive.")
        if self.coupon_frequency <= 0:
            raise ValueError("coupon_frequency must be positive.")
        periods = self.maturity_years * self.coupon_frequency
        if not np.isclose(periods, round(periods)):
            raise ValueError("maturity_years must align with coupon_frequency.")

    def cash_flows(self) -> pd.DataFrame:
        """Return coupon and principal cash flows.

        The model is accrued-free and assumes valuation just after an issue or
        coupon date. This is intentional for a stylized ALM laboratory.
        """
        periods = int(round(self.maturity_years * self.coupon_frequency))
        times = np.arange(1, periods + 1, dtype=float) / self.coupon_frequency
        coupon = self.face_value * self.coupon_rate / self.coupon_frequency
        cash_flows = np.full(periods, coupon, dtype=float)
        cash_flows[-1] += self.face_value
        return pd.DataFrame(
            {
                "bond_name": self.name,
                "time_years": times,
                "cash_flow": cash_flows,
            }
        )


def price_bond(bond: Bond, curve: ZeroCurve) -> float:
    """Price a bond as the sum of discounted future cash flows."""
    flows = bond.cash_flows()
    return present_value_from_cash_flows(flows["time_years"], flows["cash_flow"], curve)


def bond_risk_metrics(bond: Bond, curve: ZeroCurve) -> dict[str, float]:
    """Compute price, duration and convexity metrics for one bond."""
    flows = bond.cash_flows()
    times = flows["time_years"]
    cash_flows = flows["cash_flow"]
    return {
        "price": present_value_from_cash_flows(times, cash_flows, curve),
        "macaulay_duration": macaulay_duration(times, cash_flows, curve),
        "modified_duration": modified_duration(times, cash_flows, curve),
        "convexity": convexity(times, cash_flows, curve),
    }


def price_bond_portfolio(bonds: list[Bond], curve: ZeroCurve) -> pd.DataFrame:
    """Return a bond-level valuation and risk table."""
    rows = []
    for bond in bonds:
        metrics = bond_risk_metrics(bond, curve)
        rows.append(
            {
                "bond_name": bond.name,
                "face_value": bond.face_value,
                "coupon_rate": bond.coupon_rate,
                "maturity_years": bond.maturity_years,
                "coupon_frequency": bond.coupon_frequency,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def build_sample_bond_portfolio() -> list[Bond]:
    """Create a diversified synthetic fixed-income asset portfolio."""
    return [
        Bond(
            name="Short Government 2Y",
            face_value=2_000_000.0,
            coupon_rate=0.021,
            maturity_years=2.0,
            coupon_frequency=2,
        ),
        Bond(
            name="Medium Government 7Y",
            face_value=1_500_000.0,
            coupon_rate=0.028,
            maturity_years=7.0,
            coupon_frequency=2,
        ),
        Bond(
            name="Long Government 15Y",
            face_value=1_200_000.0,
            coupon_rate=0.032,
            maturity_years=15.0,
            coupon_frequency=2,
        ),
        Bond(
            name="Low Coupon 10Y",
            face_value=1_000_000.0,
            coupon_rate=0.015,
            maturity_years=10.0,
            coupon_frequency=1,
        ),
        Bond(
            name="High Coupon 20Y",
            face_value=800_000.0,
            coupon_rate=0.040,
            maturity_years=20.0,
            coupon_frequency=2,
        ),
    ]
