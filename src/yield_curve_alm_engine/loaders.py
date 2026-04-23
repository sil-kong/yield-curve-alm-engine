"""CSV loaders for user-supplied synthetic inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve
from yield_curve_alm_engine.instruments.bonds import Bond

REQUIRED_CURVE_COLUMNS = {"maturity_years", "zero_rate"}
REQUIRED_BOND_COLUMNS = {
    "name",
    "face_value",
    "coupon_rate",
    "maturity_years",
    "coupon_frequency",
}


def _read_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    return pd.read_csv(csv_path)


def _validate_required_columns(
    frame: pd.DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    missing_columns = sorted(required_columns.difference(frame.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        required = ", ".join(sorted(required_columns))
        raise ValueError(
            f"{dataset_name} CSV is missing required column(s): {missing}. "
            f"Expected columns: {required}."
        )


def _numeric_series(frame: pd.DataFrame, column: str, dataset_name: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.isna().any():
        raise ValueError(f"{dataset_name} column '{column}' must contain numeric values.")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"{dataset_name} column '{column}' must contain finite values.")
    return values


def _require_positive(values: Iterable[float], label: str) -> None:
    if np.any(np.asarray(list(values), dtype=float) <= 0):
        raise ValueError(f"{label} must be strictly positive.")


def load_zero_curve_from_csv(path: str | Path, name: str = "user_curve") -> ZeroCurve:
    """Load a zero curve from a CSV file.

    Expected columns are:
    - maturity_years
    - zero_rate
    """
    frame = _read_csv(path)
    _validate_required_columns(frame, REQUIRED_CURVE_COLUMNS, "curve")

    curve_frame = pd.DataFrame(
        {
            "maturity_years": _numeric_series(frame, "maturity_years", "curve"),
            "zero_rate": _numeric_series(frame, "zero_rate", "curve"),
        }
    ).sort_values("maturity_years")

    if curve_frame["maturity_years"].duplicated().any():
        raise ValueError("curve maturities must be unique.")
    _require_positive(curve_frame["maturity_years"], "curve maturities")

    return ZeroCurve(
        maturities=curve_frame["maturity_years"].to_numpy(dtype=float),
        zero_rates=curve_frame["zero_rate"].to_numpy(dtype=float),
        name=name,
    )


def load_bond_portfolio_from_csv(path: str | Path) -> list[Bond]:
    """Load a fixed-rate bond portfolio from a CSV file.

    Expected columns are:
    - name
    - face_value
    - coupon_rate
    - maturity_years
    - coupon_frequency
    """
    frame = _read_csv(path)
    _validate_required_columns(frame, REQUIRED_BOND_COLUMNS, "bond portfolio")

    raw_names = frame["name"]
    names = raw_names.astype(str).str.strip()
    if raw_names.isna().any() or (names == "").any():
        raise ValueError("bond portfolio column 'name' must not contain blank values.")

    face_values = _numeric_series(frame, "face_value", "bond portfolio")
    coupon_rates = _numeric_series(frame, "coupon_rate", "bond portfolio")
    maturities = _numeric_series(frame, "maturity_years", "bond portfolio")
    coupon_frequencies = _numeric_series(frame, "coupon_frequency", "bond portfolio")

    _require_positive(face_values, "bond face values")
    _require_positive(maturities, "bond maturities")
    _require_positive(coupon_frequencies, "bond coupon frequencies")

    if (coupon_rates < 0).any():
        raise ValueError("bond coupon rates cannot be negative.")
    if not np.allclose(coupon_frequencies, np.round(coupon_frequencies)):
        raise ValueError("bond coupon frequencies must be integer values.")

    bonds = []
    for row_number, name in enumerate(names, start=2):
        try:
            bonds.append(
                Bond(
                    name=name,
                    face_value=float(face_values.iloc[row_number - 2]),
                    coupon_rate=float(coupon_rates.iloc[row_number - 2]),
                    maturity_years=float(maturities.iloc[row_number - 2]),
                    coupon_frequency=int(round(coupon_frequencies.iloc[row_number - 2])),
                )
            )
        except ValueError as exc:
            raise ValueError(f"invalid bond data on CSV row {row_number}: {exc}") from exc

    return bonds
