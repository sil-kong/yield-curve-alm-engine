"""CSV loaders for user-supplied synthetic inputs."""

from __future__ import annotations

from pathlib import Path
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
REQUIRED_LIABILITY_COLUMNS = {"time_years", "cash_flow"}
# Decimal rates above 100% almost always mean the file is in percent.
MAX_ABS_ZERO_RATE = 1.0


MAX_REPORTED_ROWS = 5


def _read_csv(path: str | Path, dataset_name: str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    try:
        frame = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"{dataset_name} CSV is empty: {csv_path}") from exc
    frame.columns = [str(column).strip() for column in frame.columns]
    if frame.empty:
        raise ValueError(f"{dataset_name} CSV contains no data rows: {csv_path}")
    return frame


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


def _csv_rows(mask: np.ndarray) -> list[int]:
    """Return 1-based CSV line numbers (header is line 1) where ``mask`` is true."""
    return [int(position) + 2 for position in np.flatnonzero(mask)]


def _raise_for_rows(
    frame: pd.DataFrame,
    column: str,
    mask: pd.Series | np.ndarray,
    dataset_name: str,
    problem: str,
) -> None:
    """Raise a ValueError naming the column, rows and raw values that fail a check."""
    mask = np.asarray(mask, dtype=bool)
    if not mask.any():
        return
    rows = _csv_rows(mask)
    raw_values = frame.loc[mask, column].tolist()
    details = ", ".join(
        f"row {row}: {value!r}"
        for row, value in zip(rows[:MAX_REPORTED_ROWS], raw_values[:MAX_REPORTED_ROWS])
    )
    if len(rows) > MAX_REPORTED_ROWS:
        details += f", ... ({len(rows)} rows in total)"
    raise ValueError(f"{dataset_name} column '{column}' {problem} ({details}).")


def _numeric_series(frame: pd.DataFrame, column: str, dataset_name: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce").astype(float)
    _raise_for_rows(frame, column, values.isna(), dataset_name, "must contain numeric values")
    _raise_for_rows(
        frame, column, ~np.isfinite(values), dataset_name, "must contain finite values"
    )
    return values


def _require_positive(
    frame: pd.DataFrame,
    values: pd.Series,
    column: str,
    dataset_name: str,
) -> None:
    _raise_for_rows(frame, column, values <= 0, dataset_name, "must be strictly positive")


def _require_unique(
    frame: pd.DataFrame,
    values: pd.Series,
    column: str,
    dataset_name: str,
) -> None:
    _raise_for_rows(
        frame,
        column,
        values.duplicated(keep=False),
        dataset_name,
        "must contain unique values",
    )


def load_zero_curve_from_csv(path: str | Path, name: str = "user_curve") -> ZeroCurve:
    """Load a zero curve from a CSV file.

    Expected columns are:
    - maturity_years
    - zero_rate
    """
    frame = _read_csv(path, "curve")
    _validate_required_columns(frame, REQUIRED_CURVE_COLUMNS, "curve")

    maturities = _numeric_series(frame, "maturity_years", "curve")
    zero_rates = _numeric_series(frame, "zero_rate", "curve")
    _require_positive(frame, maturities, "maturity_years", "curve")
    _require_unique(frame, maturities, "maturity_years", "curve")
    _raise_for_rows(
        frame,
        "zero_rate",
        zero_rates.abs() > MAX_ABS_ZERO_RATE,
        "curve",
        f"looks like a percentage, expected decimal rates with |rate| <= {MAX_ABS_ZERO_RATE}",
    )
    if "curve_date" in frame.columns:
        curve_dates = frame["curve_date"].astype(str).str.strip().unique()
        if len(curve_dates) > 1:
            raise ValueError(
                "curve CSV mixes several curve_date values "
                f"({', '.join(sorted(curve_dates))}); a curve must use one observation date."
            )

    curve_frame = pd.DataFrame(
        {"maturity_years": maturities, "zero_rate": zero_rates}
    ).sort_values("maturity_years")

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
    frame = _read_csv(path, "bond portfolio")
    dataset = "bond portfolio"
    _validate_required_columns(frame, REQUIRED_BOND_COLUMNS, dataset)

    raw_names = frame["name"]
    names = raw_names.astype(str).str.strip()
    _raise_for_rows(
        frame, "name", raw_names.isna() | (names == ""), dataset, "must not contain blank values"
    )
    _require_unique(frame, names, "name", dataset)

    face_values = _numeric_series(frame, "face_value", dataset)
    coupon_rates = _numeric_series(frame, "coupon_rate", dataset)
    maturities = _numeric_series(frame, "maturity_years", dataset)
    coupon_frequencies = _numeric_series(frame, "coupon_frequency", dataset)

    _require_positive(frame, face_values, "face_value", dataset)
    _require_positive(frame, maturities, "maturity_years", dataset)
    _require_positive(frame, coupon_frequencies, "coupon_frequency", dataset)
    _raise_for_rows(frame, "coupon_rate", coupon_rates < 0, dataset, "cannot be negative")
    _raise_for_rows(
        frame,
        "coupon_rate",
        coupon_rates > 1.0,
        dataset,
        "looks like a percentage, expected decimal rates such as 0.025",
    )
    _raise_for_rows(
        frame,
        "coupon_frequency",
        ~np.isclose(coupon_frequencies, np.round(coupon_frequencies)),
        dataset,
        "must contain integer values",
    )
    periods = maturities * np.round(coupon_frequencies)
    _raise_for_rows(
        frame,
        "maturity_years",
        ~np.isclose(periods, np.round(periods)),
        dataset,
        "must be a whole number of coupon periods (maturity_years * coupon_frequency)",
    )

    bonds = [
        Bond(
            name=name,
            face_value=float(face_value),
            coupon_rate=float(coupon_rate),
            maturity_years=float(maturity),
            coupon_frequency=int(round(frequency)),
        )
        for name, face_value, coupon_rate, maturity, frequency in zip(
            names, face_values, coupon_rates, maturities, coupon_frequencies
        )
    ]

    return bonds


def load_liability_cashflows_from_csv(path: str | Path) -> pd.DataFrame:
    """Load liability cash flows from a CSV file.

    Expected columns are:
    - time_years
    - cash_flow

    Liability cash flows are positive future obligations in this project.
    """
    frame = _read_csv(path, "liability")
    _validate_required_columns(frame, REQUIRED_LIABILITY_COLUMNS, "liability")

    times = _numeric_series(frame, "time_years", "liability")
    cash_flows = _numeric_series(frame, "cash_flow", "liability")
    _require_positive(frame, times, "time_years", "liability")
    _raise_for_rows(
        frame,
        "cash_flow",
        cash_flows < 0,
        "liability",
        "must contain positive obligations (no negative values)",
    )

    liability_frame = pd.DataFrame(
        {"time_years": times, "cash_flow": cash_flows}
    ).sort_values("time_years", kind="stable")

    return liability_frame.reset_index(drop=True)
