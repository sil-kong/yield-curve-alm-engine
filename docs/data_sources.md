# Data Sources

## Scope

This project is primarily a stylized ALM and fixed-income risk laboratory. The
default curve, bond portfolio and liabilities remain synthetic so the full
workflow is reproducible without external services.

The project also supports optional public ECB yield-curve ingestion. The ECB
fetcher is intentionally isolated from the valuation workflow: it downloads a
curve, writes a clean local CSV, and the ALM scripts consume that CSV offline
through the existing `--curve-csv` option.

## ECB Yield Curve Source

The ECB publishes euro area yield curves through its public Data Portal and
Data API. The yield-curve dataset includes spot, instantaneous forward and par
yield curves across several issuer universes.

This project starts with ECB euro area government bond spot curves and uses the
spot rates as zero rates for discounting:

- `aaa`: AAA-rated euro area central government bond curve, ECB instrument code
  `G_N_A`;
- `all`: all-ratings euro area central government bond curve, ECB instrument
  code `G_N_C`.

The series keys follow the pattern:

```text
YC.B.U2.EUR.4F.<INSTRUMENT>.SV_C_YM.SR_<MATURITY>
```

Example AAA spot-rate series:

```text
YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_1Y
YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y
YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y
YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y
YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y
```

## Normalized CSV Schema

The fetch script writes a normalized CSV with this schema:

| column | description |
| --- | --- |
| `curve_date` | ECB observation date |
| `maturity_years` | maturity in years |
| `zero_rate` | decimal continuously compounded annual zero rate |
| `source` | `ECB` |
| `curve_name` | normalized curve label, such as `ecb_aaa_spot` |
| `series_key` | original ECB series key |

ECB observations are quoted in percent per annum. The fetcher converts them to
decimal rates by dividing by 100 before writing `zero_rate`.

## Usage

Fetch the latest AAA spot curve into a local ignored data directory:

```bash
yield-curve-fetch-ecb \
  --curve-type aaa \
  --date latest \
  --output data/market_curves/ecb/ecb_aaa_spot_latest.csv
```

Then run the ALM base case from local files:

```bash
yield-curve-build-base \
  --curve-csv data/market_curves/ecb/ecb_aaa_spot_latest.csv \
  --bonds-csv data/examples/portfolios/example_bond_portfolio.csv \
  --liabilities-csv data/examples/liabilities/example_liability_cashflows.csv
```

The same `--curve-csv`, `--bonds-csv` and `--liabilities-csv` arguments are
available in the stress-test and dashboard scripts.

The `python -m yield_curve_alm_engine.scripts.fetch_ecb_curve` and
`python -m yield_curve_alm_engine.scripts.build_base_case` forms remain
supported for users who do not want installed console commands.

## Reproducibility

Internet access is only needed when refreshing the ECB CSV. Once the CSV has
been fetched, valuation, stress testing, plotting and dashboard generation run
offline from local files.

Fetched market-curve files under `data/market_curves/` are ignored by Git. This
keeps the repository small and avoids accidentally committing dated downloaded
data while still making the workflow reproducible for a user who refreshes the
CSV locally.

## Limitations

This is public ECB data ingestion, not a market data management stack. The
project does not implement:

- market data entitlement, lineage or approval workflows;
- full ECB metadata management;
- EIOPA regulatory curve construction;
- bootstrapping from traded bonds or swaps;
- credit spread, liquidity premium or volatility modelling;
- industrial curve validation, stale-data checks or fallback hierarchies.

The ECB curve is used here to make the ALM examples less closed and more
realistic as a research workflow while preserving the project's transparent,
educational scope.
