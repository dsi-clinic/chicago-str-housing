"""Tract prohibition dates processor for DiD analysis.

This module aggregates building-level STR prohibition data to tract-level
treatment dates, identifying when each census tract first received an
STR prohibition (treatment).
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TractProhibitionDatesProcessor(DataProcessor):
    """Aggregate STR prohibition data to tract-level treatment dates.

    This processor:
    1. Performs spatial join to assign each building to a census tract
    2. Finds the first prohibition date for each tract
    3. Counts the number of buildings with prohibitions per tract
    4. Returns tract-level treatment dates for DiD analysis

    Tracts not in the output are considered "never treated" (control group).
    """

    def __init__(self, output_path: str | None = None) -> None:
        """Initialize the tract prohibition dates processor.

        Args:
            output_path: Optional path to save tract prohibition dates CSV
        """
        super().__init__(
            "tract_prohibition_dates",
            "Aggregate building-level STR prohibitions to tract-level treatment dates",
        )
        self.required_data = ["str_prohibition_data", "tract_boundaries"]
        self.output_path = output_path

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregate STR prohibition data to tract level.

        Required context keys:
            - str_prohibition_data: GeoDataFrame with building-level prohibition data
            - tract_boundaries: GeoDataFrame with census tract geometries

        Returns:
            Dictionary with 'tract_prohibition_dates' containing a DataFrame with columns:
            - tract_geoid: Census tract GEOID
            - first_prohibition_date: Date of first STR prohibition in the tract
            - building_count: Number of buildings with prohibitions in the tract
        """
        # Get inputs from context
        str_data = context["str_prohibition_data"].copy()
        tract_boundaries = context["tract_boundaries"]

        logger.info(
            "Aggregating STR prohibition data to tract-level treatment dates..."
        )
        logger.info("  Input STR prohibition buildings: %d", len(str_data))
        logger.info("  Census tracts available: %d", len(tract_boundaries))

        # Ensure both datasets are in the same CRS
        if str_data.crs != tract_boundaries.crs:
            str_data = str_data.to_crs(tract_boundaries.crs)

        # Step 1: Spatial join to assign each building to a census tract
        str_with_tract = gpd.sjoin(
            str_data,
            tract_boundaries[["tract_geoid", "geometry"]],
            how="left",
            predicate="within",
        )

        # Check for buildings that didn't match any tract
        unmatched = str_with_tract["tract_geoid"].isna().sum()
        if unmatched > 0:
            logger.warning(
                "  %d buildings not within any tract boundary (dropped)",
                unmatched,
            )
            str_with_tract = str_with_tract.dropna(subset=["tract_geoid"])

        logger.info("  Buildings matched to tracts: %d", len(str_with_tract))

        # Step 2: Determine which date column to use
        # The STRProhibitionDataLoader creates 'prohibition_date' from signed_date
        if "prohibition_date" in str_with_tract.columns:
            date_col = "prohibition_date"
        elif "signed_date" in str_with_tract.columns:
            date_col = "signed_date"
        elif "recorded_date" in str_with_tract.columns:
            date_col = "recorded_date"
        else:
            raise ValueError(
                "No date column found in STR prohibition data. "
                "Expected 'prohibition_date', 'signed_date', or 'recorded_date'."
            )

        logger.info("  Using date column: %s", date_col)

        # Ensure date column is datetime
        str_with_tract[date_col] = pd.to_datetime(str_with_tract[date_col])

        # Step 3: Aggregate by tract - get first prohibition date and building count
        tract_dates = (
            str_with_tract.groupby("tract_geoid")
            .agg(
                {
                    date_col: "min",  # First prohibition date in tract
                    "application_id": "count",  # Number of buildings (using any ID column)
                }
            )
            .reset_index()
        )

        # Rename columns for clarity
        tract_dates = tract_dates.rename(
            columns={
                date_col: "first_prohibition_date",
                "application_id": "building_count",
            }
        )

        # Sort by first prohibition date
        tract_dates = tract_dates.sort_values("first_prohibition_date").reset_index(
            drop=True
        )

        # Log summary statistics
        n_treated_tracts = len(tract_dates)
        n_total_tracts = len(tract_boundaries)
        n_never_treated = n_total_tracts - n_treated_tracts

        logger.info("Tract prohibition dates created successfully:")
        logger.info("  Tracts with prohibitions (treated): %d", n_treated_tracts)
        logger.info("  Tracts without prohibitions (control): %d", n_never_treated)
        logger.info(
            "  Treatment rate: %.1f%%",
            100 * n_treated_tracts / n_total_tracts,
        )
        logger.info(
            "  Date range: %s to %s",
            tract_dates["first_prohibition_date"].min().strftime("%Y-%m-%d"),
            tract_dates["first_prohibition_date"].max().strftime("%Y-%m-%d"),
        )
        logger.info(
            "  Buildings per treated tract: min=%d, median=%.0f, max=%d",
            tract_dates["building_count"].min(),
            tract_dates["building_count"].median(),
            tract_dates["building_count"].max(),
        )

        # Optionally save to CSV
        if self.output_path:
            output_file = Path(self.output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            tract_dates.to_csv(output_file, index=False)
            logger.info("  Saved to: %s", output_file)

        return {"tract_prohibition_dates": tract_dates}
