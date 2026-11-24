"""Key-rate duration and PV01 diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.risk.duration_convexity import present_value_from_cash_flows

REQUIRED_CASH_FLOW_COLUMNS = {"time_years", "cash_flow"}
REPORT_KEY_MATURITIES = [1.0, 2.0, 5.0, 10.0, 20.0, 30.0]


def _validate_cash_flows(cash_flows: pd.DataFrame) -> pd.DataFrame:
    missing_columns = REQUIRED_CASH_FLOW_COLUMNS.difference(cash_flows.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"cash_flows is missing required column(s): {missing}.")

    frame = cash_flows.loc[:, ["time_years", "cash_flow"]].copy()
    frame["time_years"] = pd.to_numeric(frame["time_years"], errors="coerce")
    frame["cash_flow"] = pd.to_numeric(frame["cash_flow"], errors="coerce")

    if frame[["time_years", "cash_flow"]].isna().any().any():
        raise ValueError("cash_flows columns must contain numeric values.")
    if (frame["time_years"] <= 0).any():
        raise ValueError("cash-flow times must be strictly positive.")

    return frame


def _default_key_maturities(curve: ZeroCurve) -> list[float]:
    return [float(maturity) for maturity in curve.maturities]


def _format_key_rate_name(key_maturity: float, shock_size: float) -> str:
    direction = "up" if shock_size >= 0 else "down"
    shock_bps = abs(shock_size) * 10_000.0
    maturity_label = f"{key_maturity:g}y"
    shock_label = f"{shock_bps:g}bp"
    return f"key_rate_{maturity_label}_{direction}_{shock_label}"


def key_rate_weights(
    maturities: np.ndarray,
    key_maturities: list[float],
    key_maturity: float,
) -> np.ndarray:
    """Return tent-basis weights of one key rate on the quoted curve maturities.

    Each key rate is a piecewise-linear "tent" that equals 1 at its own key
    maturity, falls linearly to 0 at the neighbouring key maturities and is
    flat beyond the first and last keys. The weights of all key rates sum to 1
    at every maturity, so the key-rate PV01s add up to the parallel PV01
    (up to second-order terms).
    """
    keys = np.asarray(sorted(float(key) for key in key_maturities), dtype=float)
    if keys.size == 0:
        raise ValueError("key_maturities must not be empty.")
    if np.any(keys <= 0):
        raise ValueError("key maturities must be strictly positive.")
    if np.any(np.diff(keys) <= 0):
        raise ValueError("key maturities must be unique.")
    matches = np.flatnonzero(np.isclose(keys, key_maturity))
    if matches.size == 0:
        raise ValueError("key_maturity must be one of key_maturities.")

    unit = np.zeros(keys.size)
    unit[matches[0]] = 1.0
    return np.interp(np.asarray(maturities, dtype=float), keys, unit)


def apply_key_rate_shock(
    curve: ZeroCurve,
    key_maturity: float,
    shock_size: float = 0.0001,
    width: float = 1.0,
    name: str | None = None,
    key_maturities: list[float] | None = None,
) -> ZeroCurve:
    """Return a curve with a local zero-rate shock around ``key_maturity``.

    When ``key_maturities`` is supplied, the shock uses the additive tent basis
    of :func:`key_rate_weights`. Otherwise it falls back to a standalone
    triangular shock with weight ``max(1 - abs(maturity - key_maturity) / width, 0)``;
    if that triangle does not touch any quoted point, the nearest curve
    maturity receives the full shock.
    """
    if key_maturity <= 0:
        raise ValueError("key_maturity must be strictly positive.")
    if width <= 0:
        raise ValueError("width must be strictly positive.")
    if not np.isfinite(shock_size):
        raise ValueError("shock_size must be finite.")

    maturities = np.asarray(curve.maturities, dtype=float)
    if key_maturities is not None:
        weights = key_rate_weights(maturities, key_maturities, key_maturity)
    else:
        weights = np.maximum(1.0 - np.abs(maturities - key_maturity) / width, 0.0)
        if np.allclose(weights, 0.0):
            nearest_index = int(np.argmin(np.abs(maturities - key_maturity)))
            weights[nearest_index] = 1.0

    shock_name = name or _format_key_rate_name(key_maturity, shock_size)
    return curve.with_zero_rates(curve.zero_rates + shock_size * weights, name=shock_name)


def compute_key_rate_pv01(
    cash_flows: pd.DataFrame,
    curve: ZeroCurve,
    key_maturities: list[float] | None = None,
    shock_size: float = 0.0001,
) -> pd.DataFrame:
    """Compute local PV01 and key-rate duration for generic cash flows.

    ``pv01`` is defined as ``shocked_pv - base_pv`` for a local +1 bp shock by
    default. Positive cash flows should therefore have negative PV01 values
    when rates rise. Key rates use the additive tent basis, so the ``pv01``
    column sums to the parallel PV01 of the cash flows.
    """
    if shock_size == 0:
        raise ValueError("shock_size must be non-zero.")

    frame = _validate_cash_flows(cash_flows)
    keys = key_maturities or _default_key_maturities(curve)
    base_pv = present_value_from_cash_flows(frame["time_years"], frame["cash_flow"], curve)

    rows = []
    for key_maturity in keys:
        shocked_curve = apply_key_rate_shock(
            curve=curve,
            key_maturity=float(key_maturity),
            shock_size=shock_size,
            key_maturities=list(keys),
        )
        shocked_pv = present_value_from_cash_flows(
            frame["time_years"],
            frame["cash_flow"],
            shocked_curve,
        )
        pv_change = shocked_pv - base_pv
        key_rate_duration = -pv_change / (base_pv * shock_size) if not np.isclose(base_pv, 0.0) else np.nan
        rows.append(
            {
                "key_maturity": float(key_maturity),
                "base_pv": base_pv,
                "shocked_pv": shocked_pv,
                "pv_change": pv_change,
                "pv01": pv_change,
                "key_rate_duration": key_rate_duration,
            }
        )

    return pd.DataFrame(rows)


def compute_asset_liability_key_rate_report(
    asset_cash_flows: pd.DataFrame,
    liability_cash_flows: pd.DataFrame,
    curve: ZeroCurve,
    key_maturities: list[float] | None = None,
    shock_size: float = 0.0001,
) -> pd.DataFrame:
    """Compute asset, liability and surplus key-rate PV01 diagnostics."""
    asset_report = compute_key_rate_pv01(
        asset_cash_flows,
        curve,
        key_maturities=key_maturities,
        shock_size=shock_size,
    )
    liability_report = compute_key_rate_pv01(
        liability_cash_flows,
        curve,
        key_maturities=key_maturities,
        shock_size=shock_size,
    )

    report = pd.DataFrame(
        {
            "key_maturity": asset_report["key_maturity"],
            "asset_pv01": asset_report["pv01"],
            "liability_pv01": liability_report["pv01"],
            "surplus_pv01": asset_report["pv01"] - liability_report["pv01"],
            "asset_key_rate_duration": asset_report["key_rate_duration"],
            "liability_key_rate_duration": liability_report["key_rate_duration"],
        }
    )
    report["key_rate_duration_gap"] = (
        report["asset_key_rate_duration"] - report["liability_key_rate_duration"]
    )
    return report
