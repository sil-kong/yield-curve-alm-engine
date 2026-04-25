import pytest

from yield_curve_alm_engine.loaders import (
    load_bond_portfolio_from_csv,
    load_liability_cashflows_from_csv,
    load_zero_curve_from_csv,
)


def test_load_zero_curve_from_csv(tmp_path) -> None:
    path = tmp_path / "curve.csv"
    path.write_text("maturity_years,zero_rate\n2,0.03\n1,0.02\n")

    curve = load_zero_curve_from_csv(path)

    assert curve.name == "user_curve"
    assert curve.get_zero_rate(1.5) == pytest.approx(0.025)


def test_load_bond_portfolio_from_csv(tmp_path) -> None:
    path = tmp_path / "bonds.csv"
    path.write_text(
        "name,face_value,coupon_rate,maturity_years,coupon_frequency\n"
        "Example Bond,1000,0.035,5,2\n"
    )

    bonds = load_bond_portfolio_from_csv(path)

    assert len(bonds) == 1
    assert bonds[0].name == "Example Bond"
    assert bonds[0].coupon_frequency == 2


def test_curve_loader_rejects_missing_required_columns(tmp_path) -> None:
    path = tmp_path / "bad_curve.csv"
    path.write_text("maturity_years\n1\n")

    with pytest.raises(ValueError, match="missing required column"):
        load_zero_curve_from_csv(path)


def test_load_liability_cashflows_from_csv(tmp_path) -> None:
    path = tmp_path / "liabilities.csv"
    path.write_text("time_years,cash_flow\n2,200\n1,100\n")

    liabilities = load_liability_cashflows_from_csv(path)

    assert list(liabilities["time_years"]) == [1, 2]
    assert list(liabilities["cash_flow"]) == [100, 200]
