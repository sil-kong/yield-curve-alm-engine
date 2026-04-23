"""Shared helpers for script entry points."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from yield_curve_alm_engine.curve.base_curve import ZeroCurve, create_base_zero_curve
from yield_curve_alm_engine.instruments.bonds import Bond, build_sample_bond_portfolio
from yield_curve_alm_engine.loaders import (
    load_bond_portfolio_from_csv,
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


def collect_asset_cash_flows(bonds: list[Bond]) -> pd.DataFrame:
    """Collect bond cash flows into a generic asset cash-flow table."""
    frames = [bond.cash_flows().loc[:, ["time_years", "cash_flow"]] for bond in bonds]
    return pd.concat(frames, ignore_index=True)
