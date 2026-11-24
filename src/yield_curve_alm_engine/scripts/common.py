"""Shared helpers for script entry points."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve, create_base_zero_curve
from yield_curve_alm_engine.instruments.bonds import Bond, build_sample_bond_portfolio
from yield_curve_alm_engine.instruments.liabilities import create_stylized_liability_schedule
from yield_curve_alm_engine.loaders import (
    load_bond_portfolio_from_csv,
    load_liability_cashflows_from_csv,
    load_zero_curve_from_csv,
)


def add_input_arguments(parser: argparse.ArgumentParser) -> None:
    """Add optional CSV input arguments shared by scripts."""
    parser.add_argument(
        "--curve-csv",
        type=Path,
        default=None,
        help="Optional CSV curve input with maturity_years and zero_rate columns.",
    )
    parser.add_argument(
        "--bonds-csv",
        type=Path,
        default=None,
        help="Optional CSV bond portfolio input with fixed-rate bond columns.",
    )
    parser.add_argument(
        "--liabilities-csv",
        type=Path,
        default=None,
        help="Optional CSV liability input with time_years and cash_flow columns.",
    )


def load_curve(curve_csv: Path | None) -> ZeroCurve:
    """Load a user curve if supplied, otherwise return the synthetic base curve."""
    if curve_csv is None:
        return create_base_zero_curve()
    return load_zero_curve_from_csv(curve_csv)


def load_bonds(bonds_csv: Path | None) -> list[Bond]:
    """Load a user bond portfolio if supplied, otherwise return the sample portfolio."""
    if bonds_csv is None:
        return build_sample_bond_portfolio()
    return load_bond_portfolio_from_csv(bonds_csv)


def load_liabilities(liabilities_csv: Path | None) -> pd.DataFrame:
    """Load user liabilities if supplied, otherwise return the synthetic schedule."""
    if liabilities_csv is None:
        return create_stylized_liability_schedule()
    return load_liability_cashflows_from_csv(liabilities_csv)


def collect_asset_cash_flows(bonds: list[Bond]) -> pd.DataFrame:
    """Collect bond cash flows into a generic asset cash-flow table."""
    frames = [bond.cash_flows().loc[:, ["time_years", "cash_flow"]] for bond in bonds]
    return pd.concat(frames, ignore_index=True)


SYNTHETIC_INPUT_NOTE = (
    "This output uses the built-in synthetic curve, bond portfolio and liability "
    "schedule provided for reproducible examples."
)


def _curve_source(curve_csv: Path) -> str | None:
    """Return the ``source`` recorded in a normalized curve CSV, if any."""
    try:
        sources = pd.read_csv(curve_csv, usecols=lambda column: column == "source")
    except (OSError, ValueError):
        return None
    if "source" not in sources.columns or sources.empty:
        return None
    values = sources["source"].dropna().astype(str).unique()
    return values[0] if len(values) == 1 else None


def describe_inputs(args: argparse.Namespace) -> str:
    """Describe which inputs a run used: local CSV files, ECB curve or synthetic data."""
    inputs = {
        "curve": args.curve_csv,
        "bond portfolio": args.bonds_csv,
        "liabilities": args.liabilities_csv,
    }
    supplied = [label for label, path in inputs.items() if path is not None]
    if not supplied:
        return SYNTHETIC_INPUT_NOTE

    parts = []
    for label in supplied:
        path = inputs[label]
        if label == "curve" and _curve_source(path) == "ECB":
            parts.append(f"curve from an ECB public yield-curve CSV (`{path}`)")
        else:
            parts.append(f"{label} from `{path}`")
    note = "Inputs: " + "; ".join(parts) + "."
    synthetic = [label for label in inputs if label not in supplied]
    if synthetic:
        note += f" Built-in synthetic inputs are used for: {', '.join(synthetic)}."
    note += " Valuation runs offline from local files."
    return note
