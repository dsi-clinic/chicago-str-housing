"""Deseasonalize rental prices to remove seasonal patterns.

Seasonal patterns in rental prices (summer highs, winter lows) can create
spurious pre-treatment trends if treatment timing correlates with seasons.

This processor removes month-of-year effects from rental prices by:
1. Computing the average price for each calendar month (Jan, Feb, ..., Dec)
2. Subtracting these month effects from observed prices
3. Re-centering at the overall mean

**Why deseasonalization matters for DiD:**

If STR prohibitions are concentrated in summer months (as in Chicago's 2016 wave),
and rental prices naturally peak in summer, you'll see artificial pre-treatment
trends even under parallel trends. Deseasonalization removes this confound.

**Method:**

deseasonalized_price = price - month_of_year_mean + overall_mean

This is equivalent to including month-of-year fixed effects in the regression,
but doing it upfront allows the event study to focus on treatment dynamics.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class DeseasonalizeRentalProcessor(DataProcessor):
    """Remove seasonal patterns from rental prices."""

    def __init__(self) -> None:
        """Initialize the deseasonalization processor."""
        super().__init__(
            "deseasonalized_panel",
            "Remove month-of-year seasonal effects from rental prices"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Deseasonalize rental prices in the panel."""
        logger.info("Deseasonalizing rental prices...")

        did_panel = context.get("did_panel")
        if did_panel is None:
            raise ValueError("did_panel not found in context")

        # Make a copy to avoid modifying original
        panel_deseason = did_panel.copy()

        # Extract month-of-year (1-12)
        panel_deseason["month_of_year"] = panel_deseason["month"].dt.month

        # Compute seasonal means (average price for each calendar month)
        seasonal_means = (
            panel_deseason.groupby("month_of_year")["rental_price"]
            .mean()
            .rename("seasonal_mean")
        )

        # Overall mean (for re-centering)
        overall_mean = panel_deseason["rental_price"].mean()

        # Merge seasonal means back
        panel_deseason = panel_deseason.merge(
            seasonal_means,
            left_on="month_of_year",
            right_index=True,
            how="left"
        )

        # Deseasonalize: subtract seasonal component, add back overall mean
        panel_deseason["rental_price_original"] = panel_deseason["rental_price"]
        panel_deseason["rental_price"] = (
            panel_deseason["rental_price"] -
            panel_deseason["seasonal_mean"] +
            overall_mean
        )

        # Calculate seasonal adjustment magnitude
        seasonal_adjustment = (
            panel_deseason["seasonal_mean"] - overall_mean
        )
        max_adjustment = seasonal_adjustment.abs().max()

        # Log seasonal pattern
        logger.info("Seasonal pattern detected:")
        for month_num in range(1, 13):
            month_name = pd.Timestamp(2020, month_num, 1).strftime("%B")
            month_mean = seasonal_means.loc[month_num]
            adjustment = month_mean - overall_mean
            logger.info(
                "  %s: $%.2f (adjustment: %+.2f)",
                month_name, month_mean, adjustment
            )

        logger.info(
            "Deseasonalization complete. Max seasonal adjustment: $%.2f",
            max_adjustment
        )

        # Drop temporary columns
        panel_deseason = panel_deseason.drop(
            columns=["seasonal_mean", "month_of_year"]
        )

        return {
            "did_panel": panel_deseason,
            "seasonal_means": seasonal_means,
            "max_seasonal_adjustment": max_adjustment,
        }
