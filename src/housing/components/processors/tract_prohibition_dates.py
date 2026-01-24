"""Aggregates STR prohibition dates to the census tracts"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TractProhibitionDatesProcessor(DataProcessor):
    """Aggregate STR prohibition dates to census tracts.
    
    The STR prohibition dates are aggregated to the census tracts by the tract_geoid.
    The STR prohibition dates are aggregated to the census tracts by the first_prohibition_date.
    The STR prohibition dates are aggregated to the census tracts by the number_of_buildings.
    """

    def __init__(self) -> None:
        """Initialize the STR prohibition dates processor."""
        super().__init__(
            "tract_prohibition_dates",
            "Aggregates STR prohibition dates to the census tracts",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregates STR prohibition dates to the census tracts."""
        # Get the data from context
        str_tract_data = context["str_tract_data"]
        
        # Select and rename columns
        tract_prohibition_dates = str_tract_data[[
            "tract_geoid",
            "prohibition_date",
            "str_prohibition_count",
        ]].rename(columns={
            "prohibition_date": "first_prohibition_date",
            "str_prohibition_count": "building_count",
        }).dropna(subset=["tract_geoid"])
        
        tract_prohibition_dates["first_prohibition_date"] = pd.to_datetime(tract_prohibition_dates["first_prohibition_date"])
        
        logger.info("Created STR tract summary with %d tracts", len(tract_prohibition_dates))
        logger.info("Tracts with prohibitions: %d", (tract_prohibition_dates["building_count"] > 0).sum())
        
        output_path = "/project/output/tract_prohibition_dates.csv"
        tract_prohibition_dates.to_csv(output_path, index=False)
        logger.info("Saved STR prohibition dates to: %s", output_path)
        
        return {"tract_prohibition_dates": tract_prohibition_dates}