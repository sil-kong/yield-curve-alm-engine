"""ECB yield-curve ingestion helpers.

This module is the only place in the package that performs live ECB network
access. Downstream ALM scripts consume the normalized CSV output offline through
the existing ``--curve-csv`` workflow.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import io
import warnings

import numpy as np
import pandas as pd

ECB_API_BASE_URL = "https://data-api.ecb.europa.eu/service/data/YC"
SOURCE = "ECB"

CURVE_TYPE_TO_INSTRUMENT = {
    "aaa": "G_N_A",
    "all": "G_N_C",
}
CURVE_TYPE_TO_NAME = {
    "aaa": "ecb_aaa_spot",
    "all": "ecb_all_spot",
}

SUPPORTED_MATURITIES: list[tuple[str, float]] = [
    ("3M", 0.25),
    ("6M", 0.50),
    ("1Y", 1.00),
    ("2Y", 2.00),
    ("3Y", 3.00),
    ("5Y", 5.00),
    ("7Y", 7.00),
    ("10Y", 10.00),
    ("15Y", 15.00),
    ("20Y", 20.00),
    ("30Y", 30.00),
]

NORMALIZED_COLUMNS = [
    "curve_date",
    "maturity_years",
    "zero_rate",
    "source",
    "curve_name",
    "series_key",
]


def build_series_key(curve_type: str, maturity_code: str) -> str:
    """Build a full ECB yield-curve spot-rate series key."""
    if curve_type not in CURVE_TYPE_TO_INSTRUMENT:
        valid = ", ".join(sorted(CURVE_TYPE_TO_INSTRUMENT))
        raise ValueError(f"unsupported curve_type '{curve_type}'. Expected one of: {valid}.")

    instrument = CURVE_TYPE_TO_INSTRUMENT[curve_type]
    return f"YC.B.U2.EUR.4F.{instrument}.SV_C_YM.SR_{maturity_code}"


def _series_key_for_url(series_key: str) -> str:
    if series_key.startswith("YC."):
        return series_key.removeprefix("YC.")
    return series_key


def build_ecb_url(
    series_key: str,
    date: str = "latest",
    start: str | None = None,
    end: str | None = None,
) -> str:
    """Build an ECB Data API CSV URL for one yield-curve series."""
    query: dict[str, str] = {"format": "csvdata"}

    if date != "latest":
        query["startPeriod"] = date
        query["endPeriod"] = date
    elif start or end:
        if start:
            query["startPeriod"] = start
        if end:
            query["endPeriod"] = end
    else:
        query["lastNObservations"] = "1"

    encoded_query = urlencode(query)
    return f"{ECB_API_BASE_URL}/{_series_key_for_url(series_key)}?{encoded_query}"


def _find_column(frame: pd.DataFrame, candidates: list[str]) -> str:
    normalized = {
        column.lower().replace(":", "").replace("_", "").replace(" ", ""): column
        for column in frame.columns
    }
    for candidate in candidates:
        key = candidate.lower().replace(":", "").replace("_", "").replace(" ", "")
        if key in normalized:
            return normalized[key]
    raise ValueError(f"ECB response is missing one of the expected columns: {candidates}.")


def parse_ecb_csv_response(
    csv_text: str,
    maturity_years: float,
    series_key: str,
    curve_name: str,
) -> pd.DataFrame:
    """Parse an ECB CSV response and return the normalized curve schema.

    ECB yield-curve observations are percent per annum, so ``OBS_VALUE`` is
    divided by 100 to produce decimal zero rates.
    """
    frame = pd.read_csv(io.StringIO(csv_text))
    if frame.empty:
        raise ValueError(f"ECB response for {series_key} is empty.")

    date_column = _find_column(frame, ["TIME_PERIOD", "time_period", "date"])
    value_column = _find_column(frame, ["OBS_VALUE", "obs_value", "value"])

    observations = frame.loc[:, [date_column, value_column]].copy()
    observations[date_column] = observations[date_column].astype(str)
    observations[value_column] = pd.to_numeric(observations[value_column], errors="coerce")
    observations = observations.dropna(subset=[date_column, value_column])

    if observations.empty:
        raise ValueError(f"ECB response for {series_key} contains no numeric observations.")

    observations = observations.sort_values(date_column)
    latest = observations.iloc[-1]
    zero_rate = float(latest[value_column]) / 100.0

    if not np.isfinite(zero_rate):
        raise ValueError(f"ECB response for {series_key} has a non-finite zero rate.")

    return pd.DataFrame(
        [
            {
                "curve_date": str(latest[date_column]),
                "maturity_years": float(maturity_years),
                "zero_rate": zero_rate,
                "source": SOURCE,
                "curve_name": curve_name,
                "series_key": series_key,
            }
        ],
        columns=NORMALIZED_COLUMNS,
    )


def _download_text(url: str, timeout: float = 30.0) -> str:
    request = Request(url, headers={"User-Agent": "yield-curve-alm-engine/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_ecb_curve(
    curve_type: str = "aaa",
    date: str = "latest",
    start: str | None = None,
    end: str | None = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Fetch and normalize ECB euro area spot yield-curve rates."""
    if date != "latest" and (start or end):
        raise ValueError("Use either --date or --start/--end, not both.")
    if curve_type not in CURVE_TYPE_TO_INSTRUMENT:
        valid = ", ".join(sorted(CURVE_TYPE_TO_INSTRUMENT))
        raise ValueError(f"unsupported curve_type '{curve_type}'. Expected one of: {valid}.")

    curve_name = CURVE_TYPE_TO_NAME[curve_type]
    rows = []

    for maturity_code, maturity_years in SUPPORTED_MATURITIES:
        series_key = build_series_key(curve_type, maturity_code)
        url = build_ecb_url(series_key, date=date, start=start, end=end)

        try:
            csv_text = _download_text(url, timeout=timeout)
            rows.append(
                parse_ecb_csv_response(
                    csv_text=csv_text,
                    maturity_years=maturity_years,
                    series_key=series_key,
                    curve_name=curve_name,
                )
            )
        except Exception as exc:
            warnings.warn(f"Skipping ECB maturity {maturity_code} ({series_key}): {exc}")

    if len(rows) < 4:
        raise RuntimeError(
            f"ECB fetch returned only {len(rows)} usable maturities; at least 4 are required."
        )

    curve = pd.concat(rows, ignore_index=True)
    return curve.loc[:, NORMALIZED_COLUMNS].sort_values("maturity_years").reset_index(drop=True)


def write_ecb_curve_csv(curve: pd.DataFrame, output_path: str | Path) -> Path:
    """Write a normalized ECB curve CSV."""
    missing_columns = set(NORMALIZED_COLUMNS).difference(curve.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"normalized ECB curve is missing column(s): {missing}.")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    curve.loc[:, NORMALIZED_COLUMNS].to_csv(path, index=False)
    return path
