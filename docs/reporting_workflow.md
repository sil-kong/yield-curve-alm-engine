# Reporting Workflow

## Scope

The reporting layer is designed for a professional-style research workflow. It
turns the valuation, surplus, stress-test, key-rate and cash-flow matching
diagnostics into local CSV, PNG and Markdown artifacts.

It is not production reporting, regulatory reporting or an official valuation
pack. The goal is to make the ALM mechanics easy to inspect, rerun and discuss.

## Commands

After editable installation, the installed commands are:

```bash
yield-curve-build-base
yield-curve-run-stress
yield-curve-build-dashboard
yield-curve-plot-results --publish-docs-figures
yield-curve-generate-report
```

The equivalent module commands remain available:

```bash
python -m yield_curve_alm_engine.scripts.build_base_case
python -m yield_curve_alm_engine.scripts.run_stress_tests
python -m yield_curve_alm_engine.scripts.build_alm_dashboard
python -m yield_curve_alm_engine.scripts.plot_results
python -m yield_curve_alm_engine.scripts.generate_report
```

## Offline Example

This workflow uses only local example CSV files:

```bash
yield-curve-build-base \
  --curve-csv data/examples/example_zero_curve.csv \
  --bonds-csv data/examples/portfolios/example_bond_portfolio.csv \
  --liabilities-csv data/examples/liabilities/example_liability_cashflows.csv

yield-curve-run-stress \
  --curve-csv data/examples/example_zero_curve.csv \
  --bonds-csv data/examples/portfolios/example_bond_portfolio.csv \
  --liabilities-csv data/examples/liabilities/example_liability_cashflows.csv

yield-curve-build-dashboard \
  --curve-csv data/examples/example_zero_curve.csv \
  --bonds-csv data/examples/portfolios/example_bond_portfolio.csv \
  --liabilities-csv data/examples/liabilities/example_liability_cashflows.csv

yield-curve-plot-results \
  --curve-csv data/examples/example_zero_curve.csv \
  --bonds-csv data/examples/portfolios/example_bond_portfolio.csv \
  --liabilities-csv data/examples/liabilities/example_liability_cashflows.csv \
  --publish-docs-figures

yield-curve-generate-report \
  --curve-csv data/examples/example_zero_curve.csv \
  --bonds-csv data/examples/portfolios/example_bond_portfolio.csv \
  --liabilities-csv data/examples/liabilities/example_liability_cashflows.csv \
  --output docs/sample_alm_report.md
```

## Main Artifacts

The reporting commands write artifacts under `outputs/`:

- `alm_dashboard_summary.csv`
- `alm_dashboard.md`
- `alm_report.md`
- `key_rate_report.csv`
- `cashflow_gap_report.csv`
- `stress_test_results.csv`
- `curve_scenarios.png`
- `surplus_by_scenario.png`
- `asset_liability_by_scenario.png`
- `key_rate_pv01.png`
- `cashflow_gap.png`

The `outputs/` directory is for generated local artifacts and remains ignored
except for `outputs/.gitkeep`. Curated examples for GitHub review live in:

- `docs/sample_alm_report.md`
- `docs/figures/curve_scenarios.png`
- `docs/figures/surplus_by_scenario.png`
- `docs/figures/key_rate_pv01.png`
- `docs/figures/cashflow_gap.png`

The generated figures are meant to support a recruiter or interview discussion:
curve shocks, surplus by scenario, key-rate PV01 and asset/liability cash-flow
timing gaps. They should be read together with the methodology and limitations,
not as evidence of an industrial ALM platform.
