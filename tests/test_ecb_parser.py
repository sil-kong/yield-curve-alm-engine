from pathlib import Path

import pandas as pd
import pytest

from yield_curve_alm_engine.data.ecb import (
    NORMALIZED_COLUMNS,
    build_ecb_url,
    build_series_key,
    parse_ecb_csv_response,
)
from yield_curve_alm_engine.loaders import load_zero_curve_from_csv


FIXTURE = Path(__file__).parent / "fixtures" / "ecb_yc_sample.csv"


def test_parse_ecb_csv_converts_percent_rates_to_decimal_zero_rates() -> None:
    normalized = parse_ecb_csv_response(
        csv_text=FIXTURE.read_text(),
        maturity_years=10.0,
        series_key="YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
        curve_name="ecb_aaa_spot",
    )

    assert normalized.loc[0, "curve_date"] == "2026-04-15"
    assert normalized.loc[0, "zero_rate"] == pytest.approx(0.0265)


def test_parse_ecb_csv_returns_normalized_output_schema() -> None:
    normalized = parse_ecb_csv_response(
        csv_text=FIXTURE.read_text(),
        maturity_years=10.0,
        series_key="YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
        curve_name="ecb_aaa_spot",
    )

    assert list(normalized.columns) == NORMALIZED_COLUMNS


def test_existing_curve_loader_accepts_normalized_ecb_output(tmp_path) -> None:
    normalized = pd.DataFrame(
        [
            {
                "curve_date": "2026-04-15",
                "maturity_years": 1.0,
                "zero_rate": 0.021,
                "source": "ECB",
                "curve_name": "ecb_aaa_spot",
                "series_key": "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_1Y",
            },
            {
                "curve_date": "2026-04-15",
                "maturity_years": 10.0,
                "zero_rate": 0.0265,
                "source": "ECB",
                "curve_name": "ecb_aaa_spot",
                "series_key": "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
            },
        ]
    )
    path = tmp_path / "ecb_curve.csv"
    normalized.to_csv(path, index=False)

    curve = load_zero_curve_from_csv(path)

    assert curve.get_zero_rate(1.0) == pytest.approx(0.021)
    assert curve.get_zero_rate(10.0) == pytest.approx(0.0265)


def test_build_series_key_and_latest_url() -> None:
    series_key = build_series_key("aaa", "10Y")
    url = build_ecb_url(series_key, date="latest")

    assert series_key == "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"
    assert "/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y" in url
    assert "lastNObservations=1" in url
