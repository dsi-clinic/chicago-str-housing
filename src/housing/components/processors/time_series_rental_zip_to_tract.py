"""Aggregates zip codes to tract for time series rental data"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TimeSeriesRentalZipToTractProcessor(DataProcessor):
    """Processor for time series rental data, zip codes to tracts aggregation.

    - Maps zip codes to census tracts (many-to-many relationship)
    - Handles overlapping boundaries with area-weighted aggregation
    - Census tracts provide fine-grained geographic units
    - Enables detailed neighborhood-level analysis
    """

    def __init__(self) -> None:
        """Initialize the zip to tract processor."""
        super().__init__(
            "rental_zip_to_tract", "Transform rental data from zip codes to census tracts"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation to census tract level for time series data."""
        # Get the data from context
        time_series_rental_data = context["time_series_rental_data"]
        zip_boundaries = context["zip_boundaries"]
        tract_boundaries = context["tract_boundaries"]

        # Step 1: Join rental data with zip boundaries
        zip_rental = zip_boundaries.merge(time_series_rental_data, on="zip_code", how="inner")

        # Step 2: Spatial join - zip codes to census tracts
        # Ensure same CRS
        if zip_rental.crs != tract_boundaries.crs:
            tract_boundaries = tract_boundaries.to_crs(zip_rental.crs)

        # Perform spatial join, many intersections expected due to overlapping zip/tract boundaries
        spatial_join = gpd.sjoin(
            zip_rental, tract_boundaries, how="inner", predicate="intersects"
        )

        # Step 3: Calculate intersection areas for proper weighting
        # For each zip-tract pair, calculate the actual intersection area
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
                        "date": row["date"],
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

        tract_time_series_rental = (
            intersections_df.groupby(["tract_geoid", "date"])
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
        tract_time_series_rental.columns = [
            "tract_geoid",
            "date",
            "total_weighted_rent",
            "total_area",
            "avg_rental_price",
            "min_rental_price",
            "max_rental_price",
            "zip_count",
            "geometry",
        ]

        # Calculate area-weighted average
        tract_time_series_rental["area_weighted_avg_rent"] = (
            tract_time_series_rental["total_weighted_rent"] / tract_time_series_rental["total_area"]
        )

        # Convert to GeoDataFrame
        tract_time_series_rental_gdf = gpd.GeoDataFrame(
            tract_time_series_rental, geometry="geometry", crs=tract_boundaries.crs
        )

        # Step 5: Join back with tract boundaries for final result
        final_result = tract_boundaries.merge(
            tract_time_series_rental_gdf.drop(columns=["geometry"]), on="tract_geoid", how="left"
        )

        logger.info("Sample data:\n%s", final_result.head())

        columns_to_drop = [
            "geometry", 
            "STATEFP", 
            "COUNTYFP", 
            "TRACTCE", 
            "GEOID", 
            "GEOIDFQ",
            "NAME", 
            "NAMELSAD", 
            "MTFCC", 
            "FUNCSTAT", 
            "ALAND", 
            "AWATER", 
            "INTPTLAT", 
            "INTPTLON"
        ]
        
        output_path = "/project/output/rental_panel_data.csv"
        final_result.drop(columns=columns_to_drop).to_csv(output_path, index=False)
        logger.info("Saved tract-level time series data to: %s", output_path)
        logger.info("Output shape: %d rows (tract-date combinations), %d columns", 
                   len(final_result), len(final_result.columns))
        
        return {
            "rental_panel_data": final_result,
        }
