"""Tract prohibition dates processor.

This module aggregates STR prohibition data to census tract level and finds
the first prohibition date for each tract.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TractProhibitionDatesProcessor(DataProcessor):
    """Aggregate STR prohibition data to tracts and find first prohibition date.

    This processor:
    1. Performs spatial join between STR prohibition points and tract boundaries
    2. Finds the first prohibition date per tract (minimum prohibition_date)
    3. Optionally counts buildings per tract
    4. Outputs tract-level prohibition dates DataFrame
    """

    def __init__(self):
        """Initialize the tract prohibition dates processor."""
        super().__init__(
            "tract_prohibition_dates",
            "Aggregate STR prohibition data to tracts and find first prohibition date"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregate STR prohibition data to tracts and find first prohibition date.

        Args:
            context: Pipeline context containing:
                - str_prohibition_data: GeoDataFrame with STR prohibition points
                - tract_boundaries: GeoDataFrame with tract boundaries

        Returns:
            Dictionary with 'tract_prohibition_dates' key containing DataFrame
            with columns: tract_geoid, first_prohibition_date, building_count
        """
        # Get inputs from context
        str_data = context["str_prohibition_data"]
        tract_boundaries = context["tract_boundaries"]

        logger.info("Aggregating STR prohibition data to tracts...")
        logger.info("  Input: %d STR prohibition records", len(str_data))

        # Step 1: Ensure both datasets are in same CRS
        str_data_for_join = str_data.copy()
        if str_data_for_join.crs != tract_boundaries.crs:
            str_data_for_join = str_data_for_join.to_crs(tract_boundaries.crs)
            logger.info("  Reprojected STR data to match tract CRS: %s", tract_boundaries.crs)

        # Step 2: Spatial join - which tract is each STR prohibition point in?
        points_with_tract = gpd.sjoin(
            str_data_for_join,
            tract_boundaries[["tract_geoid", "geometry"]],
            how="left",
            predicate="within",
        )

        # Count points that didn't match any tract
        unmatched = points_with_tract["tract_geoid"].isna().sum()
        if unmatched > 0:
            logger.warning("  %d STR prohibition points did not match any tract", unmatched)

        # Step 3: Filter to matched points and find first prohibition date per tract
        matched_points = points_with_tract[points_with_tract["tract_geoid"].notna()].copy()

        # Ensure prohibition_date is datetime
        if "prohibition_date" in matched_points.columns:
            if not pd.api.types.is_datetime64_any_dtype(matched_points["prohibition_date"]):
                matched_points["prohibition_date"] = pd.to_datetime(
                    matched_points["prohibition_date"], errors="coerce"
                )
        else:
            # Fallback: use signed_date or recorded_date
            if "signed_date" in matched_points.columns:
                matched_points["prohibition_date"] = pd.to_datetime(
                    matched_points["signed_date"], errors="coerce"
                )
            elif "recorded_date" in matched_points.columns:
                matched_points["prohibition_date"] = pd.to_datetime(
                    matched_points["recorded_date"], errors="coerce"
                )
            else:
                raise ValueError(
                    "No prohibition_date, signed_date, or recorded_date column found in STR data"
                )

        # Filter to valid dates
        matched_points = matched_points[matched_points["prohibition_date"].notna()].copy()

        if len(matched_points) == 0:
            logger.warning("  No STR prohibition records with valid dates found")
            return {
                "tract_prohibition_dates": pd.DataFrame(
                    columns=["tract_geoid", "first_prohibition_date", "building_count"]
                )
            }

        # Step 4: Aggregate by tract
        # Find first prohibition date (minimum date) per tract
        tract_dates = (
            matched_points.groupby("tract_geoid")
            .agg(
                {
                    "prohibition_date": "min",  # First prohibition date
                }
            )
            .reset_index()
            .rename(columns={"prohibition_date": "first_prohibition_date"})
        )

        # Count buildings per tract
        building_count = (
            matched_points.groupby("tract_geoid")
            .size()
            .reset_index(name="building_count")
        )

        # Merge dates and counts
        tract_prohibition_dates = tract_dates.merge(
            building_count, on="tract_geoid", how="left"
        )

        # Sort by tract_geoid
        tract_prohibition_dates = tract_prohibition_dates.sort_values("tract_geoid").reset_index(
            drop=True
        )

        logger.info("  Output: %d tracts with prohibition dates", len(tract_prohibition_dates))
        if len(tract_prohibition_dates) > 0:
            logger.info(
                "  Date range: %s to %s",
                tract_prohibition_dates["first_prohibition_date"].min(),
                tract_prohibition_dates["first_prohibition_date"].max(),
            )
            logger.info(
                "  Total buildings: %d",
                tract_prohibition_dates["building_count"].sum(),
            )

        return {"tract_prohibition_dates": tract_prohibition_dates}
