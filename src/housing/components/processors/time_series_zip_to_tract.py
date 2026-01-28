"""Zip code to census tract spatial processor for time series rental data.

This module performs spatial joins to transform time series rental data from zip code level
to census tract level using area-weighted aggregation.
"""

import logging
from pathlib import Path
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TimeSeriesZipToTractProcessor(DataProcessor):
    """Perform spatial join to transform time series rental data from zip code level.

    to census tract level using area-weighted aggregation.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the time series ZIP to tract processor.

        Args:
            output_dir: Optional output directory for tract panel data
        """
        super().__init__(
            "time_series_zip_to_tract",
            "Transform time series rental data from ZIP code level to census tract level using area-weighted aggregation",
        )
        self.output_dir = output_dir

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join to transform time series rental data from zip code level."""
        # Get the data from context
        rental_panel_data = context["rental_panel_data"]
        tract_boundaries = context["tract_boundaries"]
        zip_to_tract_crosswalk = context["zip_to_tract_crosswalk"]

        # Step 1: Merge panel data with crosswalk
        logger.info("Merging rental panel data with zip to tract crosswalk...")
        merged_df = rental_panel_data.merge(
            zip_to_tract_crosswalk, on="zip_code", how="inner"
        )
        print(merged_df.columns)

        # Step 2: Calculate weighted rental prices
        logger.info("Calculating weighted rental prices...")
        merged_df["weighted_rent"] = (
            merged_df["rental_price"] * merged_df["intersection_area"]
        )

        # Step 3: Aggregate to tract level for each month
        logger.info("Aggregating to tract level for each month...")
        tract_panel_data = (
            merged_df.groupby(["tract_geoid", "month"])
            .agg({"weighted_rent": "sum", "intersection_area": "sum"})
            .reset_index()
        )

        # Step 4: Normalize to get tract-level rental price
        tract_panel_data["rental_price"] = (
            tract_panel_data["weighted_rent"] / tract_panel_data["intersection_area"]
        )

        # Validation steps
        logger.info(
            "Missing values after imputation: %d",
            tract_panel_data["rental_price"].isna().sum(),
        )
        logger.info(
            "Maximum number of rows per tract-month combination: %d",
            tract_panel_data.groupby(["tract_geoid", "month"]).size().max(),
        )
        logger.info(
            "Minimum number of rows per tract-month combination: %d",
            tract_panel_data.groupby(["tract_geoid", "month"]).size().min(),
        )
        logger.info(
            "Total unique tracts: %d", tract_boundaries["tract_geoid"].nunique()
        )
        logger.info(
            "Unique tracts in panel data: %d", tract_panel_data["tract_geoid"].nunique()
        )

        # Save the tract panel data to a CSV file
        if self.output_dir is not None:
            output_path = Path(self.output_dir) / "tract_panel_data.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            tract_panel_data.to_csv(output_path, index=False)
            logger.info("Tract panel data saved to: %s", output_path)

        return {"tract_panel_data": tract_panel_data}
