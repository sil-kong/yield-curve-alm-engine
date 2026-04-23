"""Run deterministic rate stress tests for the stylized ALM balance sheet."""

from __future__ import annotations

from yield_curve_alm_engine.config import OUTPUTS
from yield_curve_alm_engine.curve.base_curve import create_base_zero_curve
from yield_curve_alm_engine.curve.shocks import get_stress_scenarios
from yield_curve_alm_engine.instruments.bonds import build_sample_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import create_stylized_liability_schedule
from yield_curve_alm_engine.risk.surplus import (
    compare_bond_sensitivities,
    run_surplus_scenarios,
)


def main() -> None:
    base_curve = create_base_zero_curve()
    bonds = build_sample_bond_portfolio()
    liabilities = create_stylized_liability_schedule()
    scenarios = get_stress_scenarios()

    stress_results = run_surplus_scenarios(
        bonds=bonds,
        liabilities=liabilities,
        base_curve=base_curve,
        scenarios=scenarios,
        include_base=True,
    )
    bond_sensitivities = compare_bond_sensitivities(
        bonds=bonds,
        base_curve=base_curve,
        scenarios=scenarios,
    )

    stress_results.to_csv(OUTPUTS / "stress_test_results.csv", index=False)
    bond_sensitivities.to_csv(OUTPUTS / "bond_sensitivities.csv", index=False)

    display_columns = [
        "scenario",
        "asset_value",
        "liability_value",
        "surplus",
        "asset_value_change",
        "liability_value_change",
        "surplus_change",
    ]
    print("\nStress Test Results")
    print("-------------------")
    print(stress_results[display_columns].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nSaved stress-test outputs to: {OUTPUTS}")


if __name__ == "__main__":
    main()
