"""Census tract to community area aggregation processor.

This module aggregates tract-level rental data up to community area level using
area-weighted aggregation and centroid-based spatial joins.
"""

import logging
from typing import Any

import geopandas as gpd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class STRBuildingsToCommunityProcessor(DataProcessor):
    """Aggregate STR buildings tract-level data up to community areas."""

    def __init__(self) -> None:
        """Initialize STR tract to community processor."""
        super().__init__(
            "str_buildings_tract_to_community",
            "Aggregate STR tract building data to community areas",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregates tracts into community levels"""
        logger.info("Aggregating STR building tract data to community areas...")

        # Grab STR tract data and community boundaries
        tract_data = context["str_buildings_tract_data_clean"]
        community_boundaries = context["community_boundaries"]

        logger.info("Columns in str_tract_data: %s", tract_data.columns.tolist())

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
        community_agg = (
            tract_community.groupby("community_name")
            .agg({"str_buildings_count": "sum"})
            .reset_index()
        )

        # Step 3: Merge back with community boundaries
        final_result = community_boundaries.merge(
            community_agg, on="community_name", how="left"
        )

        # Step 4: Calculate community area (in km²) and density
        logger.info("Calculating community area and STR density...")

        # Convert to projected CRS for accurate area calculation (UTM Zone 16N covers Chicago)
        final_result = final_result.to_crs("EPSG:32616")

        # Compute area in square kilometers
        final_result["area_km2"] = final_result.geometry.area / 1_000_000

        # Fill any missing counts with 0 before computing density
        final_result["str_buildings_count"] = final_result[
            "str_buildings_count"
        ].fillna(0)

        logger.info(
            "Building count range: %.2f - %.2f",
            final_result["str_buildings_count"].min(),
            final_result["str_buildings_count"].max(),
        )

        # Compute density (listings per km²)
        final_result["str_buildings_density"] = (
            final_result["str_buildings_count"] / final_result["area_km2"]
        )

        # Convert back to WGS84 for plotting
        final_result = final_result.to_crs("EPSG:4326")

        logger.info(
            "Density range: %.2f - %.2f listings/km²",
            final_result["str_buildings_density"].min(),
            final_result["str_buildings_density"].max(),
        )

        logger.info("Final result: %d community areas", len(final_result))

        return {"str_buildings_community_data": final_result}
