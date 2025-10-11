"""Census tract to community area aggregation processor.

This module aggregates tract-level rental data up to community area level using
area-weighted aggregation and centroid-based spatial joins.
"""

import logging
from typing import Any

import geopandas as gpd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TractToCommunityProcessor(DataProcessor):
    """Aggregate tract-level data up to community areas.

    Census tracts are designed to nest within larger geographies, providing
    clearer spatial relationships. This processor aggregates tract-level data
    from the zip-to-tract join up to the community area level.
    """

    def __init__(self) -> None:
        """Initialize the tract to community processor."""
        super().__init__(
            "tract_to_community", "Aggregate census tract data to community areas"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregate tract data to community level."""
        logger.info("Aggregating tract data to community areas...")

        # Get the data from context
        tract_data = context["tract_rental_data"]
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

        # Filter to tracts with rental data
        tract_community_clean = tract_community.dropna(
            subset=["avg_rental_price", "community_name"]
        )

        # Calculate area-weighted aggregates
        # Convert to projected CRS (UTM Zone 16N for Chicago) for accurate area calculations
        # Note: tract_community_clean currently has centroid geometries, so we need original tract geometries
        # Get original geometries from tract_data
        original_geometries = tract_data.set_index("tract_geoid")["geometry"]
        tract_community_clean = tract_community_clean.set_index("tract_geoid")
        tract_community_clean["original_geometry"] = original_geometries
        tract_community_clean = tract_community_clean.reset_index()

        # Convert to projected CRS and calculate area
        temp_gdf = gpd.GeoDataFrame(
            tract_community_clean, geometry="original_geometry", crs=tract_data.crs
        )
        temp_gdf_projected = temp_gdf.to_crs("EPSG:32616")
        tract_community_clean["tract_area"] = temp_gdf_projected.geometry.area

        tract_community_clean["weighted_rent"] = (
            tract_community_clean["avg_rental_price"]
            * tract_community_clean["tract_area"]
        )

        community_agg = (
            tract_community_clean.groupby("community_name")
            .agg(
                {
                    "weighted_rent": "sum",
                    "tract_area": "sum",
                    "avg_rental_price": ["mean", "min", "max", "count"],
                }
            )
            .reset_index()
        )

        # Flatten column names
        community_agg.columns = [
            "community_name",
            "total_weighted_rent",
            "total_area",
            "avg_rental_price",
            "min_rental_price",
            "max_rental_price",
            "tract_count",
        ]

        # Calculate area-weighted average
        community_agg["area_weighted_avg_rent"] = (
            community_agg["total_weighted_rent"] / community_agg["total_area"]
        )

        # Step 3: Join back with community boundaries for final result
        final_result = community_boundaries.merge(
            community_agg, on="community_name", how="left"
        )

        logger.info("Final result: %d community areas", len(final_result))
        logger.info(
            "Communities with rental data: %d",
            final_result["avg_rental_price"].notna().sum(),
        )

        return {"community_rental_data": final_result}
