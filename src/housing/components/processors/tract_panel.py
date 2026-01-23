"""Aggregates zip codes to tract for time series rental data"""

import logging
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TimeSeriesZipToTractProcessor(DataProcessor):
    """Processor for time series rental data, zip codes to tracts aggregation.

    - Maps zip codes to census tracts (many-to-many relationship)
    - Handles overlapping boundaries with area-weighted aggregation
    - Census tracts provide fine-grained geographic units
    - Enables detailed neighborhood-level analysis
    """

    def __init__(self) -> None:
        """Initialize the zip to tract processor."""
        super().__init__(
            "tract_panel_data",
            "Transform rental data from zip codes to census tracts",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation to census tract level for time series data."""
        # Get the data from context
        zip_panel = context["rental_panel_data"]
        crosswalk = context["zip_to_tract_crosswalk"]

        # Step 1. Merge zip panel with crosswalk
        merged = zip_panel.merge(crosswalk, on="zip_code", how="inner")

        # Step 2: Calculate weighted rental prices
        merged["weighted_rent"] = merged["rental_price"] * merged["intersection_area"]

        # Step 3: Aggregate to tract level for each month
        tract_time_series_rental_panel = (
            merged.groupby(["tract_geoid", "month"])
            .agg(
                {
                    "weighted_rent": "sum",
                    "intersection_area": "sum",  # Total weight for normalization
                }
            )
            .reset_index()
        )

        # Step 4: Normalize to get tract-level rental price
        tract_time_series_rental_panel["rental_price"] = (
            tract_time_series_rental_panel["weighted_rent"]
            / tract_time_series_rental_panel["intersection_area"]
        )

        tract_panel = tract_time_series_rental_panel[
            ["tract_geoid", "month", "rental_price"]
        ].copy()
        tract_panel = tract_panel.sort_values(["tract_geoid", "month"])

        output_path = "/project/output/tract_panel_data.csv"

        logger.info("Total observations: %d", len(tract_panel))
        logger.info(
            "Rental price range: $%.0f - $%.0f",
            tract_panel["rental_price"].min(),
            tract_panel["rental_price"].max(),
        )

        logger.info("Sample data:\n%s", tract_panel.head())

        tract_panel.to_csv(output_path, index=False)
        logger.info("Saved tract-level time series data to: %s", output_path)
        logger.info(
            "Output shape: %d rows (tract-date combinations), %d columns",
            len(tract_panel),
            len(tract_panel.columns),
        )

        return {
            "tract_panel_data": tract_panel,
        }
