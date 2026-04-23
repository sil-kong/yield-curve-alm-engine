# yield-curve-alm-engine

A compact Python research lab for stylized yield-curve, fixed-income and
asset-liability management analytics.

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
- revalue assets and liabilities under deterministic rate shocks;
- compare balance-sheet surplus across scenarios;
- export simple CSV reports and matplotlib charts.

## Repository Structure

```text
.
├── LICENSE
├── README.md
├── requirements.txt
├── .gitignore
├── outputs/
│   └── .gitkeep
└── src/
    └── yield_curve_alm_engine
        ├── __init__.py
        ├── config.py
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
        │   ├── duration_convexity.py
        │   └── surplus.py
        └── scripts
            ├── __init__.py
            ├── build_base_case.py
            ├── run_stress_tests.py
            └── plot_results.py
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
.venv/bin/pip install -r requirements.txt
env PYTHONPATH=src .venv/bin/python src/yield_curve_alm_engine/scripts/build_base_case.py
env PYTHONPATH=src .venv/bin/python src/yield_curve_alm_engine/scripts/run_stress_tests.py
env PYTHONPATH=src .venv/bin/python src/yield_curve_alm_engine/scripts/plot_results.py
```

## Example Outputs

The scripts generate CSV and PNG artifacts in `outputs/`:

- `base_curve.csv`
- `base_case_bonds.csv`
- `base_case_liabilities.csv`
- `base_case_summary.csv`
- `stress_test_results.csv`
- `bond_sensitivities.csv`
- `curve_scenarios.png`
- `surplus_by_scenario.png`
- `asset_liability_by_scenario.png`

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

- add unit tests for curve interpolation, bond pricing and stress results;
- add modern packaging metadata with editable installation;
- add CSV input templates for custom curves and portfolios;
- add key-rate duration by maturity bucket;
- support additional liability shapes and scenario sets;
- add simple immunization diagnostics.
