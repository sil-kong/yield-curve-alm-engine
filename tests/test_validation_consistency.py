"""Regression tests for column-level validation and cross-module consistency."""

from argparse import Namespace

import numpy as np
import pandas as pd
import pytest

from yield_curve_alm_engine.curve.base_curve import ZeroCurve, create_base_zero_curve
from yield_curve_alm_engine.curve.shocks import get_stress_scenarios
from yield_curve_alm_engine.data.ecb import check_single_curve_date
from yield_curve_alm_engine.instruments.bonds import Bond, build_sample_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import create_stylized_liability_schedule
from yield_curve_alm_engine.loaders import (
    load_bond_portfolio_from_csv,
    load_liability_cashflows_from_csv,
    load_zero_curve_from_csv,
)
from yield_curve_alm_engine.risk.duration_convexity import present_value_from_cash_flows
from yield_curve_alm_engine.risk.key_rate import (
    REPORT_KEY_MATURITIES,
    compute_key_rate_pv01,
    key_rate_weights,
)
from yield_curve_alm_engine.risk.surplus import compare_bond_sensitivities
from yield_curve_alm_engine.scripts.common import (
    SYNTHETIC_INPUT_NOTE,
    collect_asset_cash_flows,
    describe_inputs,
)

BOND_HEADER = "name,face_value,coupon_rate,maturity_years,coupon_frequency\n"


def _write(tmp_path, name: str, text: str):
    path = tmp_path / name
    path.write_text(text)
    return path


# --- Key-rate PV01 ---------------------------------------------------------


def test_key_rate_weights_form_a_partition_of_unity() -> None:
    maturities = create_base_zero_curve().maturities
    total = sum(
        key_rate_weights(maturities, REPORT_KEY_MATURITIES, key) for key in REPORT_KEY_MATURITIES
    )
    np.testing.assert_allclose(total, 1.0)


@pytest.mark.parametrize("key_maturities", [None, REPORT_KEY_MATURITIES])
def test_key_rate_pv01_sums_to_parallel_pv01(key_maturities) -> None:
    curve = create_base_zero_curve()
    for cash_flows in [
        collect_asset_cash_flows(build_sample_bond_portfolio()),
        create_stylized_liability_schedule(),
    ]:
        base_pv = present_value_from_cash_flows(cash_flows["time_years"], cash_flows["cash_flow"], curve)
        parallel_pv = present_value_from_cash_flows(
            cash_flows["time_years"],
            cash_flows["cash_flow"],
            curve.with_zero_rates(curve.zero_rates + 0.0001, name="parallel_1bp"),
        )
        report = compute_key_rate_pv01(cash_flows, curve, key_maturities=key_maturities)

        assert report["pv01"].sum() == pytest.approx(parallel_pv - base_pv, rel=1e-3)


# --- Bond sensitivities ----------------------------------------------------


def test_bond_sensitivities_handle_repeated_bond_names() -> None:
    curve = ZeroCurve(maturities=[1.0, 5.0, 10.0], zero_rates=[0.02, 0.025, 0.03])
    bonds = [
        Bond("Same", 100.0, 0.02, 2.0, 1),
        Bond("Same", 100.0, 0.05, 10.0, 1),
    ]

    table = compare_bond_sensitivities(bonds, curve, get_stress_scenarios())

    first_scenario = table[table["scenario"] == "parallel_up_100bps"]
    assert len(first_scenario) == 2
    assert first_scenario["base_price"].nunique() == 2


# --- CSV loaders: row-level messages ---------------------------------------


def test_curve_loader_reports_offending_row_and_value(tmp_path) -> None:
    path = _write(tmp_path, "curve.csv", "maturity_years,zero_rate\n1,0.02\n2,abc\n")

    with pytest.raises(ValueError, match=r"'zero_rate'.*row 3: 'abc'"):
        load_zero_curve_from_csv(path)


def test_curve_loader_rejects_percent_rates(tmp_path) -> None:
    path = _write(tmp_path, "curve.csv", "maturity_years,zero_rate\n1,2.1\n2,2.2\n")

    with pytest.raises(ValueError, match="percentage"):
        load_zero_curve_from_csv(path)


def test_curve_loader_rejects_duplicate_maturities_with_rows(tmp_path) -> None:
    path = _write(tmp_path, "curve.csv", "maturity_years,zero_rate\n1,0.02\n1,0.021\n")

    with pytest.raises(ValueError, match=r"unique.*row 2.*row 3"):
        load_zero_curve_from_csv(path)


def test_curve_loader_rejects_mixed_curve_dates(tmp_path) -> None:
    path = _write(
        tmp_path,
        "curve.csv",
        "curve_date,maturity_years,zero_rate\n2026-11-20,1,0.02\n2026-11-19,2,0.021\n",
    )

    with pytest.raises(ValueError, match="curve_date"):
        load_zero_curve_from_csv(path)


def test_bond_loader_rejects_duplicate_names(tmp_path) -> None:
    path = _write(tmp_path, "bonds.csv", BOND_HEADER + "A,100,0.02,2,1\nA,100,0.03,5,1\n")

    with pytest.raises(ValueError, match="'name' must contain unique values"):
        load_bond_portfolio_from_csv(path)


def test_bond_loader_reports_misaligned_maturity_row(tmp_path) -> None:
    path = _write(tmp_path, "bonds.csv", BOND_HEADER + "A,100,0.02,2,2\nB,100,0.02,2.25,2\n")

    with pytest.raises(ValueError, match=r"'maturity_years'.*row 3: 2.25"):
        load_bond_portfolio_from_csv(path)


def test_bond_loader_rejects_percent_coupons(tmp_path) -> None:
    path = _write(tmp_path, "bonds.csv", BOND_HEADER + "A,100,2.5,2,1\n")

    with pytest.raises(ValueError, match="percentage"):
        load_bond_portfolio_from_csv(path)


def test_loader_rejects_header_only_file(tmp_path) -> None:
    path = _write(tmp_path, "liabilities.csv", "time_years,cash_flow\n")

    with pytest.raises(ValueError, match="no data rows"):
        load_liability_cashflows_from_csv(path)


def test_loader_rejects_empty_file(tmp_path) -> None:
    path = _write(tmp_path, "liabilities.csv", "")

    with pytest.raises(ValueError, match="empty"):
        load_liability_cashflows_from_csv(path)


def test_loader_accepts_padded_header(tmp_path) -> None:
    path = _write(tmp_path, "liabilities.csv", "time_years, cash_flow\n1,100\n2,110\n")

    frame = load_liability_cashflows_from_csv(path)

    assert list(frame.columns) == ["time_years", "cash_flow"]


# --- ECB curve date consistency --------------------------------------------


def test_ecb_curve_with_one_date_is_accepted() -> None:
    curve = pd.DataFrame({"curve_date": ["2026-11-20"] * 2, "maturity_years": [1.0, 2.0]})

    check_single_curve_date(curve)


def test_ecb_curve_with_mixed_dates_is_rejected() -> None:
    curve = pd.DataFrame(
        {"curve_date": ["2026-11-20", "2026-11-19"], "maturity_years": [1.0, 2.0]}
    )

    with pytest.raises(RuntimeError, match=r"2026-11-19: 2Y.*2026-11-20: 1Y"):
        check_single_curve_date(curve)


# --- Input description in dashboard and report ----------------------------


def test_describe_inputs_without_csv_is_synthetic() -> None:
    args = Namespace(curve_csv=None, bonds_csv=None, liabilities_csv=None)

    assert describe_inputs(args) == SYNTHETIC_INPUT_NOTE


def test_describe_inputs_detects_ecb_source_and_synthetic_rest(tmp_path) -> None:
    curve_path = _write(
        tmp_path,
        "my_curve.csv",
        "curve_date,maturity_years,zero_rate,source\n2026-11-20,1,0.02,ECB\n2026-11-20,2,0.021,ECB\n",
    )
    args = Namespace(curve_csv=curve_path, bonds_csv=None, liabilities_csv=None)

    note = describe_inputs(args)

    assert "ECB" in note
    assert "synthetic inputs are used for: bond portfolio, liabilities" in note
