# Methodology

## Project Scope

This repository is a stylized ALM and fixed-income risk laboratory. It is
designed to make the mechanics of yield-curve valuation, duration risk,
key-rate sensitivities and surplus stress testing transparent and reproducible.

The project uses synthetic curve, asset and liability inputs. It is not an
industrial ALM system, a regulatory model, an actuarial production platform or a
source of investment advice.

## Yield Curve

The project represents rates with a simple zero-coupon curve. Zero rates are
continuously compounded and discount factors are computed as:

```text
DF(t) = exp(-r(t) * t)
```

Rates between quoted maturity points are linearly interpolated. Rates outside
the quoted maturity range use flat extrapolation at the nearest endpoint. This
is intentionally simple and does not perform market bootstrapping.

## Bond Portfolio

Assets are stylized fixed-rate bullet bonds. Each bond produces coupon cash
flows and a final principal repayment. Prices are computed by discounting the
full future cash-flow stream on the zero curve.

The model does not include accrued interest, settlement dates, day-count
conventions, holiday calendars, embedded options, credit spreads or liquidity
adjustments.

## Liabilities

Liabilities are represented as positive future cash outflows. The default
liability schedule is synthetic and generated inside the codebase. Liability
present value is computed by discounting those positive outflows on the same
zero curve used for assets.

The current liability model is not actuarial. It does not include mortality,
lapse, inflation, policyholder behavior, expenses or stochastic claims.

## Surplus

The balance-sheet surplus convention is:

```text
surplus = asset market value - liability present value
```

Assets and liabilities are both valued under the same curve in each scenario so
the surplus analysis isolates the effect of deterministic rate movements.

## Duration and Convexity

The project computes Macaulay duration, modified duration and convexity from
dated cash flows. Under continuous compounding, modified duration is the
first-order sensitivity to a parallel shift in continuously compounded zero
rates.

The duration-based surplus impact is a first-order approximation. Full
scenario revaluation remains the more direct diagnostic when a stressed curve is
available.

## Key-Rate Duration

Key-rate diagnostics decompose sensitivity by maturity bucket. The
implementation applies a local triangular shock around each key maturity and
revalues the cash flows.

For a +1 bp shock, PV01 is reported as:

```text
pv01 = shocked PV - base PV
```

Positive cash flows therefore usually have negative PV01 under an upward rate
shock. Asset PV01, liability PV01 and surplus PV01 are reported separately.

The triangular shock is a pedagogical approximation. It is not a replacement for
curve risk systems with calibrated key-rate tenors, smooth basis functions or
instrument-level market risk infrastructure.

## Cash-Flow Matching

Cash-flow matching diagnostics aggregate asset and liability cash flows into
regular maturity buckets. The report shows:

- asset cash flow;
- liability cash flow;
- annual net cash flow;
- cumulative asset, liability and net cash flow.

This helps identify timing gaps between asset proceeds and liability outflows.
It does not include reinvestment assumptions, liquidity constraints or dynamic
portfolio rebalancing.

## Stress Testing

The scenario module includes deterministic curve stresses:

- parallel up;
- parallel down;
- steepener;
- flattener;
- curvature shock.

Each scenario returns a new zero-curve object, then assets, liabilities and
surplus are revalued. These stresses are intentionally simple and explainable.

## Limitations

The project deliberately omits:

- market curve bootstrapping from traded instruments;
- real market data ingestion;
- Solvency II or other regulatory capital calculations;
- credit spreads, default risk and recovery assumptions;
- stochastic interest-rate models;
- realistic actuarial liability modelling;
- inflation-linked liabilities;
- accounting, taxation, expenses and liquidity constraints;
- production-grade calendars, settlement logic and day-count conventions.

The project is best read as a transparent ALM mechanics lab suitable for
learning, experimentation and portfolio demonstration.
