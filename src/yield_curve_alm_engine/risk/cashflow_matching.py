"""Cash-flow bucketing and matching diagnostics."""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_CASH_FLOW_COLUMNS = {"time_years", "cash_flow"}


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


def bucket_cash_flows(
    cash_flows: pd.DataFrame,
    bucket_size: float = 1.0,
    horizon: float | None = None,
    label: str = "cash_flow",
) -> pd.DataFrame:
    """Aggregate dated cash flows into regular maturity buckets.

    Convention: bucket index is ``ceil(time_years / bucket_size)``. Therefore a
    cash flow at exactly ``t=1`` with annual buckets belongs to the ``0-1``
    bucket, while a cash flow at ``t=1.01`` belongs to ``1-2``.
    """
    if bucket_size <= 0:
        raise ValueError("bucket_size must be strictly positive.")
    if horizon is not None and horizon <= 0:
        raise ValueError("horizon must be strictly positive when supplied.")
    if not label:
        raise ValueError("label must not be blank.")

    frame = _validate_cash_flows(cash_flows)
    max_time = float(frame["time_years"].max())
    if horizon is not None and max_time > horizon:
        raise ValueError("horizon must be greater than or equal to the maximum cash-flow time.")

    bucket_count = int(np.ceil((horizon or max_time) / bucket_size))
    bucket_indices = np.ceil(frame["time_years"] / bucket_size).astype(int)
    frame["bucket_index"] = bucket_indices

    bucketed = (
        frame.groupby("bucket_index", as_index=False)["cash_flow"]
        .sum()
        .rename(columns={"cash_flow": label})
    )

    all_buckets = pd.DataFrame({"bucket_index": np.arange(1, bucket_count + 1, dtype=int)})
    result = all_buckets.merge(bucketed, on="bucket_index", how="left")
    result[label] = result[label].fillna(0.0)
    result["bucket_start"] = (result["bucket_index"] - 1) * bucket_size
    result["bucket_end"] = result["bucket_index"] * bucket_size

    return result.loc[:, ["bucket_start", "bucket_end", label]]


def build_cashflow_gap_report(
    asset_cash_flows: pd.DataFrame,
    liability_cash_flows: pd.DataFrame,
    bucket_size: float = 1.0,
    horizon: float | None = None,
) -> pd.DataFrame:
    """Build annual asset/liability cash-flow gap and cumulative gap report."""
    if horizon is None:
        asset_frame = _validate_cash_flows(asset_cash_flows)
        liability_frame = _validate_cash_flows(liability_cash_flows)
        horizon = float(max(asset_frame["time_years"].max(), liability_frame["time_years"].max()))

    asset_buckets = bucket_cash_flows(
        asset_cash_flows,
        bucket_size=bucket_size,
        horizon=horizon,
        label="asset_cash_flow",
    )
    liability_buckets = bucket_cash_flows(
        liability_cash_flows,
        bucket_size=bucket_size,
        horizon=horizon,
        label="liability_cash_flow",
    )

    report = asset_buckets.merge(
        liability_buckets,
        on=["bucket_start", "bucket_end"],
        how="outer",
    ).sort_values(["bucket_start", "bucket_end"])

    report["asset_cash_flow"] = report["asset_cash_flow"].fillna(0.0)
    report["liability_cash_flow"] = report["liability_cash_flow"].fillna(0.0)
    report["net_cash_flow"] = report["asset_cash_flow"] - report["liability_cash_flow"]
    report["cumulative_asset_cash_flow"] = report["asset_cash_flow"].cumsum()
    report["cumulative_liability_cash_flow"] = report["liability_cash_flow"].cumsum()
    report["cumulative_net_cash_flow"] = report["net_cash_flow"].cumsum()

    return report.reset_index(drop=True)
