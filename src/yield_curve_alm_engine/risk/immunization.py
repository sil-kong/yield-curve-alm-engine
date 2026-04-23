"""Simple duration-gap diagnostics for stylized ALM analysis."""

from __future__ import annotations


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
        "duration_gap_years": asset_modified_duration - liability_modified_duration,
        "asset_value_change_per_1bp_up": asset_change,
        "liability_value_change_per_1bp_up": liability_change,
        "surplus_change_per_1bp_up": asset_change - liability_change,
    }
