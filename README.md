# yield-curve-alm-engine

This repository is a stylized ALM and fixed-income risk laboratory. It is
designed to make the mechanics of yield-curve valuation, duration risk,
key-rate sensitivities and surplus stress testing transparent and reproducible.

This repository is designed as a portfolio-quality educational project. It uses
only synthetic, hard-coded inputs in its base case and does not ingest market
data. The goal is to show clear Python structure and core ALM mechanics, not to
present an industrial ALM engine, a regulatory model or a production valuation
platform.

## Motivation

ALM connects market curves, asset cash flows, liability cash flows and
balance-sheet surplus. This project keeps that setup deliberately small and
transparent so the calculations can be read, tested and extended without hiding
behind external data feeds or heavy frameworks.

The current implementation can:

- build a synthetic continuously compounded zero-coupon curve;
- price a stylized portfolio of fixed-rate bullet bonds;
- generate a synthetic liability cash-flow profile;
- compute present value, duration and convexity metrics;
- compute key-rate PV01 and duration diagnostics;
- compare asset and liability cash-flow timing gaps;
- revalue assets and liabilities under deterministic rate shocks;
- compare balance-sheet surplus across scenarios;
- produce a compact ALM dashboard export;
- export simple CSV reports and matplotlib charts.

## CV / Portfolio Highlights

- `src/` layout with editable installation through `pyproject.toml`.
- Unit tests and a lightweight GitHub Actions test workflow.
- Clear separation between curves, instruments, risk analytics and scripts.
- Reproducible synthetic examples with optional CSV inputs.
- ALM diagnostics covering surplus, duration gap, key-rate PV01 and cash-flow matching.
- Explicit documentation of assumptions, data provenance and limitations.

See [docs/methodology.md](docs/methodology.md) for the modelling conventions and
limitations.

## Repository Structure

```text
.
├── .github/
│   └── workflows/
│       └── tests.yml
├── LICENSE
├── README.md
├── docs/
│   └── methodology.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── data/
│   └── examples/
│       ├── example_bond_portfolio.csv
│       └── example_zero_curve.csv
├── outputs/
│   └── .gitkeep
└── src/
    └── yield_curve_alm_engine
        ├── __init__.py
        ├── config.py
        ├── loaders.py
        ├── curve
        │   ├── __init__.py
        │   ├── base_curve.py
        │   └── shocks.py
        ├── instruments
        │   ├── __init__.py
        │   ├── bonds.py
        │   └── liabilities.py
        ├── risk
        │   ├── __init__.py
        │   ├── cashflow_matching.py
        │   ├── duration_convexity.py
        │   ├── immunization.py
        │   ├── key_rate.py
        │   └── surplus.py
        └── scripts
            ├── common.py
            ├── __init__.py
            ├── build_alm_dashboard.py
            ├── build_base_case.py
            ├── run_stress_tests.py
            └── plot_results.py
└── tests/
    ├── test_alm_dashboard.py
    ├── test_bonds.py
    ├── test_cashflow_matching.py
    ├── test_curve.py
    ├── test_immunization.py
    ├── test_key_rate.py
    ├── test_loaders.py
    └── test_surplus.py
```

## Data Provenance

The base case uses internal synthetic data only:

- zero curve: hard-coded maturities and zero rates in
  `src/yield_curve_alm_engine/curve/base_curve.py`;
- bond portfolio: hard-coded fixed-rate bond examples in
  `src/yield_curve_alm_engine/instruments/bonds.py`;
- liabilities: synthetic annual cash flows generated in
  `src/yield_curve_alm_engine/instruments/liabilities.py`.

There is no Bloomberg, FRED, EIOPA, exchange, broker, accounting system or
actuarial data ingestion in the current version. The numbers are intentionally
illustrative and should not be interpreted as market observations.

The project can also read user-supplied CSV files for the zero curve and bond
portfolio. Those files are treated as external scenario inputs, not validated
market data.

## Financial Methodology

### Zero Curve

The base curve is a synthetic zero-coupon curve with maturities from 0.5 to 30
years. Rates are continuously compounded and interpolated linearly:

```text
DF(t) = exp(-r(t) * t)
```

Flat extrapolation is used outside the quoted maturity range.

### Bond Pricing

Bonds are stylized fixed-rate bullet instruments. Each bond generates coupon
and principal cash flows, and the price is the sum of discounted future cash
flows. The model is accrued-free and assumes valuation just after an issue or
coupon date.

### Liabilities

Liabilities are represented as annual positive cash outflows over 20 years. The
default schedule is synthetic and hump-shaped to make duration and surplus
sensitivity meaningful without pretending to use market or actuarial data.

### Duration and Convexity

The risk module computes Macaulay duration, modified duration and convexity from
generic dated cash flows. Under continuous compounding, modified duration equals
Macaulay duration for a parallel shift in zero rates.

### Duration Gap Diagnostic

The base-case summary includes a simple first-order duration-gap diagnostic. It
approximates the surplus impact of a 1 bp parallel rate increase using asset and
liability modified durations. This is a reading aid for ALM intuition, not a
hedging recommendation.

### Surplus

The core ALM metric is:

```text
surplus = asset market value - liability present value
```

Asset market value is the sum of bond prices. Liability present value is the
discounted value of future liability cash flows.

### Stress Tests

The project includes deterministic yield-curve scenarios:

- `parallel_up_100bps`
- `parallel_down_100bps`
- `steepener`
- `flattener`
- `curvature_shock`

Each stress returns a new curve object, then assets, liabilities and surplus are
revalued consistently.

## How To Run

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m yield_curve_alm_engine.scripts.build_base_case
.venv/bin/python -m yield_curve_alm_engine.scripts.run_stress_tests
.venv/bin/python -m yield_curve_alm_engine.scripts.build_alm_dashboard
.venv/bin/python -m yield_curve_alm_engine.scripts.plot_results
```

The `requirements.txt` file is retained as a minimal runtime dependency list,
but editable installation through `pyproject.toml` is the preferred development
workflow.

## User CSV Inputs

The scripts can use the built-in synthetic inputs or user-provided CSV files.
Example files are provided in `data/examples/`.

```bash
.venv/bin/python -m yield_curve_alm_engine.scripts.build_base_case \
  --curve-csv data/examples/example_zero_curve.csv \
  --bonds-csv data/examples/example_bond_portfolio.csv

.venv/bin/python -m yield_curve_alm_engine.scripts.run_stress_tests \
  --curve-csv data/examples/example_zero_curve.csv \
  --bonds-csv data/examples/example_bond_portfolio.csv
```

Expected zero-curve CSV columns:

| column | description |
| --- | --- |
| `maturity_years` | maturity in years, strictly positive |
| `zero_rate` | continuously compounded annual zero rate in decimal form |

Expected bond portfolio CSV columns:

| column | description |
| --- | --- |
| `name` | bond label |
| `face_value` | notional principal |
| `coupon_rate` | annual coupon rate in decimal form |
| `maturity_years` | maturity in years |
| `coupon_frequency` | integer number of coupon payments per year |

The CSV loader performs basic schema and numeric validation. It does not add
market conventions such as day count, calendars, settlement dates or accrued
interest.

## Example Outputs

The scripts generate CSV and PNG artifacts in `outputs/`:

- `alm_dashboard_summary.csv`
- `alm_dashboard.md`
- `base_curve.csv`
- `base_case_bonds.csv`
- `base_case_liabilities.csv`
- `base_case_summary.csv`
- `stress_test_results.csv`
- `bond_sensitivities.csv`
- `key_rate_report.csv`
- `cashflow_gap_report.csv`
- `curve_scenarios.png`
- `surplus_by_scenario.png`
- `asset_liability_by_scenario.png`
- `key_rate_pv01.png`
- `cashflow_gap.png`

## Limitations

This is a stylized educational and research lab. It deliberately omits:

- market data ingestion;
- bootstrapping from traded instruments;
- credit spreads and default risk;
- inflation-linked or stochastic liabilities;
- taxes, expenses, liquidity constraints and capital requirements;
- production-grade day count conventions, calendars and accrued interest;
- stochastic interest-rate models.

The goal is conceptual clarity, reproducible examples and readable engineering.
The project should not be used for trading, reporting, regulatory submissions or
real balance-sheet decisions.

## Future Extensions

Good next steps include:

- add user-supplied liability cash-flow CSV input;
- compare built-in and user-input portfolios in one report;
- support additional liability shapes and scenario sets;
- broaden tests around script entry points and invalid CSV cases;
- add a small command-line wrapper for common workflows.
