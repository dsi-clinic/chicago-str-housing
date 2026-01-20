"""Zip code to census tract spatial processor.

This module performs spatial joins to transform rental data from zip code level
to census tract level using area-weighted aggregation.
"""

import logging
import warnings
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)

# Suppress pandas fragmentation warning
pd.options.mode.copy_on_write = True

warnings.filterwarnings(
    "ignore",
    message=".*highly fragmented.*",
    category=pd.errors.PerformanceWarning,
)


def _identify_date_columns(df: pd.DataFrame) -> list[str]:
    """Identify date columns in the rental data.

    ZORI dataset uses date columns starting with "20" (e.g., "2010-01", "2020-12").
    This function filters columns that start with "20" to identify time series columns.

    Args:
        df: DataFrame containing rental data with potential date columns

    Returns:
        List of column names that represent date columns
    """
    return [col for col in df.columns if col.startswith("20")]


class TimeSeriesZipToTractProcessor(DataProcessor):
    """Perform spatial join to transform data from zip codes to census tracts.

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
        # Get the data from context
        zip_rental = context["rental_data"]
        tract_boundaries = context["tract_boundaries"]

        logger.info("Loaded %d zip codes with rental data", len(zip_rental))

        # Step 1: Identify date columns (all columns starting with "20")
        date_columns = [col for col in zip_rental.columns if col.startswith("20")]

        if not date_columns:
            raise ValueError(
                "No date columns found in rental data. Expected columns starting with '20'."
            )

        logger.info("Found %d date columns in rental data", len(date_columns))
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

                intersection_row = {
                    "zip_code": row["zip_code"],
                    "tract_geoid": row.get("tract_geoid", "unknown"),
                    "intersection_area": intersection_area,
                    "tract_geometry": tract_geom,
                }

                for date_col in date_columns:
                    intersection_row[date_col] = row.get(date_col)

                intersection_data.append(intersection_row)

        # Create dataframe with intersection data
        intersections_df = pd.DataFrame(intersection_data)

        # Step 4: Calculate weighted rents for each date column using vectorized operations
        # Build all weighted columns at once to avoid fragmentation
        weighted_cols = {
            f"{date_col}_weighted": intersections_df[date_col]
            * intersections_df["intersection_area"]
            for date_col in date_columns
        }
        intersections_df = intersections_df.assign(**weighted_cols)

        # Step 5: Aggregate rental prices by census tract for all date columns
        # Build aggregation dictionary - only weighted sums and geometry
        agg_dict = {
            "intersection_area": "sum",
            "tract_geometry": "first",
        }

        # Add aggregations for weighted columns (sum)
        for date_col in date_columns:
            weighted_col = f"{date_col}_weighted"
            agg_dict[weighted_col] = "sum"

        tract_rental = (
            intersections_df.groupby("tract_geoid").agg(agg_dict).reset_index()
        )

        # Flatten column names
        new_columns = ["tract_geoid", "total_area", "geometry"]

        # Add weighted_sum column for each date
        for date_col in date_columns:
            new_columns.append(f"{date_col}_weighted_sum")

        tract_rental.columns = new_columns

        # Calculate area-weighted average using vectorized operations
        # Build all average columns at once to avoid fragmentation
        avg_cols = {
            f"{date_col}_area_weighted_avg_rent": (
                tract_rental[f"{date_col}_weighted_sum"] / tract_rental["total_area"]
            )
            for date_col in date_columns
        }
        tract_rental = tract_rental.assign(**avg_cols)

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
            "tract_rental_data": final_result,
            "zip_to_tract_crosswalk": crosswalk,
        }
