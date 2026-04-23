"""Simple duration-gap diagnostics for stylized ALM analysis."""

from __future__ import annotations


def compute_duration_gap(
    asset_value: float,
    liability_value: float,
    asset_duration: float,
    liability_duration: float,
) -> float:
    """Return a simple ALM duration gap.

    Convention:

    ``duration_gap = asset_duration - (liability_value / asset_value) * liability_duration``

    Liabilities are valued as positive obligations. A negative gap means that,
    after scaling liability duration by the funding ratio, liabilities are more
    rate-sensitive than assets in first-order terms.
    """
    if asset_value <= 0:
        raise ValueError("asset_value must be strictly positive.")
    if liability_value < 0:
        raise ValueError("liability_value cannot be negative.")
    return asset_duration - (liability_value / asset_value) * liability_duration


def estimate_parallel_surplus_impact(
    asset_value: float,
    liability_value: float,
    asset_duration: float,
    liability_duration: float,
    shock_size: float,
) -> float:
    """Estimate first-order surplus impact from a parallel rate shock."""
    asset_change = -asset_duration * asset_value * shock_size
    liability_change = -liability_duration * liability_value * shock_size
    return asset_change - liability_change


def _duration_from_metrics(metrics: dict[str, float]) -> float:
    if "modified_duration" in metrics:
        return float(metrics["modified_duration"])
    if "duration" in metrics:
        return float(metrics["duration"])
    raise ValueError("bond metrics must include 'modified_duration' or 'duration'.")


def solve_two_bond_immunization(
    short_bond_metrics: dict[str, float],
    long_bond_metrics: dict[str, float],
    target_value: float,
    target_duration: float,
) -> dict[str, float]:
    """Solve a two-bond market-value allocation for a target value and duration.

    The returned ``short_weight`` and ``long_weight`` are market-value amounts,
    not tradeable notionals. This is a pedagogical two-equation allocation, not
    an optimizer with constraints, liquidity, transaction costs or lot sizes.
    """
    if target_value <= 0:
        raise ValueError("target_value must be strictly positive.")

    short_duration = _duration_from_metrics(short_bond_metrics)
    long_duration = _duration_from_metrics(long_bond_metrics)
    duration_spread = long_duration - short_duration
    if duration_spread == 0:
        raise ValueError("bond durations must be different.")

    short_weight = target_value * (long_duration - target_duration) / duration_spread
    long_weight = target_value - short_weight
    portfolio_duration = (short_weight * short_duration + long_weight * long_duration) / target_value

    return {
        "short_weight": short_weight,
        "long_weight": long_weight,
        "portfolio_value": short_weight + long_weight,
        "portfolio_duration": portfolio_duration,
        "target_value": target_value,
        "target_duration": target_duration,
        "duration_error": portfolio_duration - target_duration,
    }


def duration_gap_diagnostic(
    asset_value: float,
    liability_value: float,
    asset_modified_duration: float,
    liability_modified_duration: float,
) -> dict[str, float]:
    """Return first-order surplus sensitivity to a 1 bp parallel rate increase.

    This is a diagnostic only. It approximates the value change from modified
    duration and does not replace a full revaluation or a hedge construction.
    """
    rate_step = 0.0001
    asset_change = -asset_value * asset_modified_duration * rate_step
    liability_change = -liability_value * liability_modified_duration * rate_step

    return {
        "duration_gap_years": compute_duration_gap(
            asset_value,
            liability_value,
            asset_modified_duration,
            liability_modified_duration,
        ),
        "asset_liability_duration_difference": asset_modified_duration - liability_modified_duration,
        "asset_value_change_per_1bp_up": asset_change,
        "liability_value_change_per_1bp_up": liability_change,
        "surplus_change_per_1bp_up": estimate_parallel_surplus_impact(
            asset_value,
            liability_value,
            asset_modified_duration,
            liability_modified_duration,
            rate_step,
        ),
    }
