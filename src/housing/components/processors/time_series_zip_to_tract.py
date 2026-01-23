"""Time series ZIP to tract processor.

This module converts ZIP-level rental panel data to tract-level panel data
using a crosswalk approach with normalized area weights.
"""

from typing import Any

import pandas as pd

from pipeline.base import DataProcessor


class TimeSeriesZipToTractProcessor(DataProcessor):
    """Convert ZIP-level rental panel to tract-level panel.

    This processor:
    1. Uses a crosswalk mapping ZIP codes to census tracts
    2. Normalizes weights so they sum to 1 for each ZIP code
    3. Aggregates rental prices by tract and month using weighted averages
    4. Outputs a panel DataFrame with tract_geoid, month, rental_price
    """

    def __init__(self):
        """Initialize the time series ZIP to tract processor."""
        super().__init__(
            "zip_to_tract_panel",
            "Convert ZIP-level rental panel to tract-level panel"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Convert ZIP-level panel to tract-level panel.

        Args:
            context: Pipeline context containing:
                - rental_panel_data: DataFrame with zip_code, month, rental_price
                - zip_to_tract_crosswalk: DataFrame with zip_code, tract_geoid, intersection_area

        Returns:
            Dictionary with 'rental_panel_data' key containing tract-level panel DataFrame
            with columns: tract_geoid, month, rental_price
        """
        # Get inputs from context
        zip_panel = context["rental_panel_data"]  # From TimeSeriesRentalLoader
        crosswalk = context["zip_to_tract_crosswalk"]  # From ZipToTractProcessor

        # Step 1: Normalize crosswalk weights to sum to 1 for each ZIP code
        # Calculate total intersection area for each ZIP code
        zip_totals = crosswalk.groupby("zip_code")["intersection_area"].sum().reset_index()
        zip_totals = zip_totals.rename(columns={"intersection_area": "total_area"})

        # Merge to get total area for each ZIP-tract pair
        crosswalk_normalized = crosswalk.merge(zip_totals, on="zip_code", how="left")

        # Calculate normalized weight (proportion of ZIP code area in each tract)
        crosswalk_normalized["weight"] = (
            crosswalk_normalized["intersection_area"] / crosswalk_normalized["total_area"]
        )

        # Keep only necessary columns
        crosswalk_normalized = crosswalk_normalized[["zip_code", "tract_geoid", "weight"]]

        # Step 2: Merge panel data with crosswalk
        merged = zip_panel.merge(crosswalk_normalized, on="zip_code", how="inner")

        # Step 3: Calculate weighted rental prices
        merged["weighted_rent"] = merged["rental_price"] * merged["weight"]

        # Step 4: Aggregate to tract level for each month
        tract_panel = (
            merged.groupby(["tract_geoid", "month"])
            .agg({
                "weighted_rent": "sum",
                "weight": "sum"  # Total weight for normalization
            })
            .reset_index()
        )

        # Step 5: Normalize to get tract-level rental price
        tract_panel["rental_price"] = (
            tract_panel["weighted_rent"] / tract_panel["weight"]
        )

        # Clean up
        tract_panel = tract_panel[["tract_geoid", "month", "rental_price"]]
        tract_panel = tract_panel.sort_values(["tract_geoid", "month"])

        return {"tract_panel_data": tract_panel}
