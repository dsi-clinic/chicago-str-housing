"""Tract prohibition dates processor.

This module processes tract-level prohibition dates for analysis.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TractProhibitionDatesProcessor(DataProcessor):
    """Process tract-level prohibition dates.

    This processor handles the processing of prohibition dates at the
    tract level for use in analysis pipelines.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the tract prohibition dates processor.

        Args:
            output_dir: Optional output directory for csv data
        """
        super().__init__(
            "tract_prohibition_dates",
            "Process tract-level prohibition dates",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the tract prohibition dates processing.

        Args:
            context: Pipeline context dictionary containing required data.

        Returns:
            Dictionary with output key containing the processed data.

        Raises:
            KeyError: If required data keys are missing from context.
            ValueError: If input data does not have expected columns.
        """
        #load data from context
        str_data = context["str_prohibition_data"]
        tract_boundaries = context["tract_boundaries"]

        # Ensure both datasets are in same CRS
        if str_data.crs != tract_boundaries.crs:
            str_data = str_data.to_crs(tract_boundaries.crs)

        # Spatial join - which tract is each point in?
        str_with_tract = gpd.sjoin(
            str_data,
            tract_boundaries[["tract_geoid", "geometry"]],
            how="left",
            predicate="within",
        )

        logger.info("Matched %d buildings with tracts.", len(str_with_tract))

        # Find the first prohibition in each tract and log its date
        tract_prohib_dates = str_with_tract.groupby("tract_geoid")[["prohibition_date"]].min().reset_index()

        tract_prohib_dates = tract_prohib_dates.rename({"prohibition_date": "first_prohibition_date"}, axis=1)
        
        logger.info("Found prohibition dates for %d tracts", len(tract_prohib_dates))

        # Save output to CSV
        output_path = Path(self.output_dir) / "tract_prohibition_dates.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tract_prohib_dates.to_csv(output_path, index=False)
        logger.info("Saved tract prohibition dates to: %s", output_path)
        
        return {"tract_prohibition_dates": tract_prohib_dates}
