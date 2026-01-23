"""Zip code to census tract spatial processor.

This module performs spatial joins to transform rental data from zip code level
to census tract level using area-weighted aggregation.

It also converts the DataFrame to panel time-series format.
"""

import logging
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TimeSeriesZipToTractProcessor(DataProcessor):
    """Perform spatial join to transform data from zip codes to census tracts.

    - Maps zip codes to census tracts (many-to-many relationship)
    - Handles overlapping boundaries with area-weighted aggregation
    - Census tracts provide fine-grained geographic units
    - Enables detailed neighborhood-level analysis
    """

    def __init__(self) -> None:
        """Initialize the zip to tract processor."""
        super().__init__(
            "zip_to_tract_panel",
            "Transform time-series panel rental data from zip codes to census tracts",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation to census tract level."""
        # Get the data and crosswalk from context
        zip_rental = context["rental_panel_data"]
        crosswalk = context["zip_to_tract_crosswalk"]

        logger.info("Loaded %d zip codes with rental data", len(zip_rental))

        # Merge panel data with crosswalk
        zip_tract_merge = zip_rental.merge(crosswalk, on="zip_code", how="inner")
        logger.info(
            "Matched %d zip codes with tracts",
            len(zip_tract_merge["zip_code"].unique()),
        )

        # Calculate the spatial-weighted average rents for each tract
        zip_tract_merge["weighted_rental_price"] = (
            zip_tract_merge["rental_price"] * zip_tract_merge["intersection_area"]
        )
        tract_panel = (
            zip_tract_merge.groupby(["tract_geoid", "month"])
            .agg(
                {
                    "weighted_rental_price": "sum",
                    "intersection_area": "sum",  # Total weight for normalization
                }
            )
            .reset_index()
        )

        tract_panel["rental_price"] = (
            tract_panel["weighted_rental_price"] / tract_panel["intersection_area"]
        )

        tract_panel = tract_panel.drop(
            ["weighted_rental_price", "intersection_area"], axis=1
        )

        return {
            "tract_panel_data": tract_panel,
        }
