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


class TractToCommunityProcessor(DataProcessor):
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

        # Calculate area for weighting if needed
        tract_community_clean = self._calculate_tract_areas(
            tract_community_clean, tract_data
        )

        # Build aggregation dictionary
        agg_dict = {
            self.id_column: "count",  # Count tracts
            "tract_area": "sum",  # Sum of areas
        }

        # Add area-weighted aggregations for specified columns
        for col in self.area_weighted_columns:
            if col in tract_community_clean.columns:
                weight_col = f"weighted_{col}"
                tract_community_clean[weight_col] = (
                    tract_community_clean[col] * tract_community_clean["tract_area"]
                )
                agg_dict[weight_col] = "sum"

        # Add custom aggregations
        agg_dict.update(self.aggregate_columns)

        # Perform aggregation
        community_agg = (
            tract_community_clean.groupby("community_name").agg(agg_dict).reset_index()
        )

        # Flatten MultiIndex columns if they exist
        if isinstance(community_agg.columns, pd.MultiIndex):
            community_agg.columns = [
                "_".join(col).strip() if col[1] else col[0]
                for col in community_agg.columns.to_numpy()
            ]

        # Rename count column
        count_col_name = (
            f"{self.id_column}_count"
            if f"{self.id_column}_count" in community_agg.columns
            else self.id_column
        )
        community_agg = community_agg.rename(columns={count_col_name: "tract_count"})

        # Rename rental-specific columns to match expected naming convention
        column_renames = {}
        if "avg_rental_price_mean" in community_agg.columns:
            column_renames["avg_rental_price_mean"] = "avg_rental_price"
        if "avg_rental_price_min" in community_agg.columns:
            column_renames["avg_rental_price_min"] = "min_rental_price"
        if "avg_rental_price_max" in community_agg.columns:
            column_renames["avg_rental_price_max"] = "max_rental_price"

        community_agg = community_agg.rename(columns=column_renames)

        # Calculate area-weighted averages
        for col in self.area_weighted_columns:
            weight_col = f"weighted_{col}"
            # The aggregation adds _sum suffix, so look for that
            weight_col_sum = f"{weight_col}_sum"

            if weight_col_sum in community_agg.columns:
                # Use standard naming convention for rental data
                if col == "avg_rental_price":
                    area_weighted_col = "area_weighted_avg_rent"
                else:
                    area_weighted_col = f"area_weighted_{col}"
                community_agg[area_weighted_col] = (
                    community_agg[weight_col_sum] / community_agg["tract_area_sum"]
                )
            else:
                logger.warning(
                    "Weighted column %s not found in aggregated data", weight_col_sum
                )

        # Step 3: Join back with community boundaries for final result
        final_result = community_boundaries.merge(
            community_agg, on="community_name", how="left"
        )

        logger.info("Final result: %d community areas", len(final_result))
        logger.info(
            "Communities with tract data: %d",
            final_result["tract_count"].notna().sum(),
        )

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
