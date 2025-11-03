"""Census tract to community area aggregation processor.

This module aggregates tract-level data up to community area level using
area-weighted aggregation and centroid-based spatial joins. It's designed
to work with any tract-level dataset, not just rental data.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class ACSTractToCommunityProcessor(DataProcessor):
    """Aggregate tract-level data up to community areas.

    This processor aggregates tract-level data to community area level using
    area-weighted aggregation for numeric columns and spatial joins for
    geographic assignment. It's designed to work with any tract-level dataset.

    Args:
        input_key: Context key for input tract-level data (default: "tract_data")
        output_key: Context key for output community-level data (default: "community_data")
        id_column: Column to use for counting tracts (default: "tract_geoid")
        aggregate_columns: Dict of {column: aggregation_method} for additional stats
                          e.g., {"avg_rental_price": "mean"} or {"price": ["mean", "median"]}
        area_weighted_columns: List of columns to aggregate using area weighting
    """

    def __init__(
        self,
        input_key: str = "tract_data",
        output_key: str = "community_data",
        id_column: str = "tract_geoid",
        aggregate_columns: dict[str, str | list[str]] | None = None,
        area_weighted_columns: list[str] | None = None,
    ) -> None:
        """Initialize the tract to community processor."""
        super().__init__(
            f"tract_to_community_{input_key}",
            f"Aggregate {input_key} tract-level data to community areas",
        )
        self.input_key = input_key
        self.output_key = output_key
        self.id_column = id_column
        self.aggregate_columns = aggregate_columns or {}
        self.area_weighted_columns = area_weighted_columns or []

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregate tract data to community level."""
        logger.info("Aggregating %s tract data to community areas...", self.input_key)

        # Get the data from context
        tract_data = context[self.input_key]
        community_boundaries = context["community_boundaries"]

        # Step 1: Spatial join to find which community each tract belongs to
        logger.info("Step 1: Determining tract-to-community relationships...")

        # Use centroid-based join for nested geographies
        tract_centroids = tract_data.copy()
        tract_centroids["geometry"] = tract_centroids.geometry.centroid

        # Ensure same CRS
        if tract_centroids.crs != community_boundaries.crs:
            community_boundaries = community_boundaries.to_crs(tract_centroids.crs)

        # Spatial join - which community does each tract belong to?
        tract_community = gpd.sjoin(
            tract_centroids,
            community_boundaries[["community_name", "geometry"]],
            how="left",
            predicate="within",
        )

        logger.info(
            "Mapped %d tracts to community areas",
            tract_community["community_name"].notna().sum(),
        )

        # Step 2: Aggregate tract data by community
        logger.info("Step 2: Aggregating tract data by community area...")

        # Filter to tracts with community assignment
        tract_community_clean = tract_community.dropna(subset=["community_name"])

        if len(tract_community_clean) == 0:
            logger.warning("No tracts mapped to community areas!")
            return {self.output_key: community_boundaries}

        # Perform aggregation
        community_agg = (
            tract_community_clean.groupby("community_name")
            .agg(
                total_population=("population", "sum"),
                total_income=("median_house_income", "sum"),
            )
            .reset_index()
        )

        # Step 3: Join back with community boundaries for final result
        final_result = community_boundaries.merge(
            community_agg, on="community_name", how="left"
        )

        final_result = final_result.to_crs("EPSG:32616")

        final_result["area_km2"] = final_result.geometry.area / 1_000_000
        final_result["population_density"] = (
            final_result["total_population"] / final_result["area_km2"]
        )
        logger.info("Final result: %d community areas", len(final_result))
        logger.info("Final result columns: %s", tract_data.columns.to_list())
        logger.info("Final result columns: %s", final_result.columns.to_list())

        return {self.output_key: final_result}

    def _calculate_tract_areas(
        self, tract_community_clean: gpd.GeoDataFrame, tract_data: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """Calculate tract areas for weighting.

        Args:
            tract_community_clean: GeoDataFrame with tract-community mapping
            tract_data: Original tract data with geometries

        Returns:
            GeoDataFrame with tract areas added
        """
        # Get original geometries from tract_data
        original_geometries = tract_data.set_index(self.id_column)["geometry"]
        tract_community_clean = tract_community_clean.set_index(self.id_column)
        tract_community_clean["original_geometry"] = original_geometries
        tract_community_clean = tract_community_clean.reset_index()

        # Convert to projected CRS and calculate area
        temp_gdf = gpd.GeoDataFrame(
            tract_community_clean, geometry="original_geometry", crs=tract_data.crs
        )
        temp_gdf_projected = temp_gdf.to_crs("EPSG:32616")
        tract_community_clean["tract_area"] = temp_gdf_projected.geometry.area

        return tract_community_clean
