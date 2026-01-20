"""Zip code to census tract spatial processor for time series rental data.

This module performs spatial joins to transform time series rental data from zip code level
to census tract level using area-weighted aggregation.
"""

from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

class TimeSeriesZipToTractProcessor(DataProcessor):
    """Perform spatial join to transform time series rental data from zip code level
    to census tract level using area-weighted aggregation.
    """

    def __init__(self) -> None:
        """Initialize the time series zip to tract processor."""
        super().__init__(
            "time_series_zip_to_tract", "Transform time series rental data from zip code level to census tract level using area-weighted aggregation"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join to transform time series rental data from zip code level
        to census tract level using area-weighted aggregation.
        """
        # Get the data from context
        time_series_rental_data = context["time_series_rental_data"]
        zip_boundaries = context["zip_boundaries"]
        tract_boundaries = context["tract_boundaries"]

        # Step 1: Join time series rental data with zip boundaries
        zip_rental = zip_boundaries.merge(time_series_rental_data, on="zip_code", how="inner")

        # Step 2: Spatial join - zip codes to census tracts
        # Ensure same CRS for spatial operations
        if zip_rental.crs != tract_boundaries.crs:
            tract_boundaries = tract_boundaries.to_crs(zip_rental.crs)

        # Perform spatial join
        # Census tracts provide more granular geographic units
        # Many intersections expected due to overlapping zip/tract boundaries
        spatial_join = gpd.sjoin(
            zip_rental, tract_boundaries, how="inner", predicate="intersects"
        )

        # Step 3: Calculate intersection areas for proper weighting
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

        # Step 4: Aggregate rental prices by census tract

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

        # Create zip-to-tract crosswalk
        crosswalk = intersections_df[
            ["zip_code", "tract_geoid", "intersection_area"]
        ].copy()
        crosswalk = crosswalk.sort_values(
            ["zip_code", "intersection_area"], ascending=[True, False]
        )

        return {
            "time_series_tract_rental_data": final_result,
            "time_series_zip_to_tract_crosswalk": crosswalk,
        }