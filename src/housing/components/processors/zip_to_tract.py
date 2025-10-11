"""Zip code to census tract spatial processor.

This module performs spatial joins to transform rental data from zip code level
to census tract level using area-weighted aggregation.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class ZipToTractProcessor(DataProcessor):
    """Perform spatial join to transform data from zip codes to census tracts.

    This is the ADVANCED CONCEPT for granular analysis:
    - Maps zip codes to census tracts (many-to-many relationship)
    - Handles overlapping boundaries with area-weighted aggregation
    - Census tracts provide fine-grained geographic units
    - Enables detailed neighborhood-level analysis
    """

    def __init__(self) -> None:
        """Initialize the zip to tract processor."""
        super().__init__(
            "zip_to_tract", "Transform rental data from zip codes to census tracts"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation to census tract level."""
        logger.info("Performing spatial join: zip codes -> census tracts")

        # Get the data from context
        rental_data = context["rental_data"]
        zip_boundaries = context["zip_boundaries"]
        tract_boundaries = context["tract_boundaries"]

        # Step 1: Join rental data with zip boundaries
        logger.info("Step 1: Joining rental data with zip boundaries...")
        zip_rental = zip_boundaries.merge(rental_data, on="zip_code", how="inner")
        logger.info("Joined %d zip codes with rental data", len(zip_rental))

        # Step 2: Spatial join - zip codes to census tracts
        logger.info("Step 2: Performing spatial join (zip codes -> census tracts)...")

        # Ensure same CRS for spatial operations
        if zip_rental.crs != tract_boundaries.crs:
            tract_boundaries = tract_boundaries.to_crs(zip_rental.crs)

        # Perform spatial join
        # Census tracts provide more granular geographic units
        # Many intersections expected due to overlapping zip/tract boundaries
        spatial_join = gpd.sjoin(
            zip_rental, tract_boundaries, how="inner", predicate="intersects"
        )

        logger.info("Spatial join resulted in %d zip-tract pairs", len(spatial_join))

        # Step 3: Calculate intersection areas for proper weighting
        logger.info("Step 3: Calculating intersection areas for weighting...")

        # For each zip-tract pair, calculate the actual intersection area
        # This is crucial for accurate aggregation
        intersection_data = []

        for _, row in spatial_join.iterrows():
            zip_geom = row.geometry
            tract_idx = row.get("index_right")

            if tract_idx is not None and tract_idx in tract_boundaries.index:
                tract_geom = tract_boundaries.loc[tract_idx, "geometry"]
                intersection = zip_geom.intersection(tract_geom)
                intersection_area = intersection.area

                intersection_data.append(
                    {
                        "zip_code": row["zip_code"],
                        "tract_geoid": row.get("tract_geoid", "unknown"),
                        "rental_price": row["rental_price"],
                        "intersection_area": intersection_area,
                        "tract_geometry": tract_geom,
                    }
                )

        # Create dataframe with intersection data
        intersections_df = pd.DataFrame(intersection_data)
        logger.info(
            "Calculated intersections for %d zip-tract pairs", len(intersections_df)
        )

        # Step 4: Aggregate rental prices by census tract
        logger.info("Step 4: Aggregating rental prices by census tract...")

        # Calculate area-weighted average rental price
        intersections_df["weighted_rent"] = (
            intersections_df["rental_price"] * intersections_df["intersection_area"]
        )

        tract_rental = (
            intersections_df.groupby("tract_geoid")
            .agg(
                {
                    "weighted_rent": "sum",
                    "intersection_area": "sum",
                    "rental_price": ["mean", "min", "max", "count"],
                    "tract_geometry": "first",
                }
            )
            .reset_index()
        )

        # Flatten column names
        tract_rental.columns = [
            "tract_geoid",
            "total_weighted_rent",
            "total_area",
            "avg_rental_price",
            "min_rental_price",
            "max_rental_price",
            "zip_count",
            "geometry",
        ]

        # Calculate area-weighted average
        tract_rental["area_weighted_avg_rent"] = (
            tract_rental["total_weighted_rent"] / tract_rental["total_area"]
        )

        # Convert to GeoDataFrame
        tract_rental_gdf = gpd.GeoDataFrame(
            tract_rental, geometry="geometry", crs=tract_boundaries.crs
        )

        # Step 5: Join back with tract boundaries for final result
        final_result = tract_boundaries.merge(
            tract_rental_gdf.drop(columns=["geometry"]), on="tract_geoid", how="left"
        )

        logger.info("Final result: %d census tracts", len(final_result))
        logger.info(
            "Tracts with rental data: %d",
            final_result["avg_rental_price"].notna().sum(),
        )

        # Create zip-to-tract crosswalk
        crosswalk = intersections_df[
            ["zip_code", "tract_geoid", "intersection_area"]
        ].copy()
        crosswalk = crosswalk.sort_values(
            ["zip_code", "intersection_area"], ascending=[True, False]
        )

        logger.info("Created zip-to-tract crosswalk with %d mappings", len(crosswalk))

        return {
            "tract_rental_data": final_result,
            "zip_to_tract_crosswalk": crosswalk,
        }
