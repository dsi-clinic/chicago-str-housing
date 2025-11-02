"""Point data to census tract aggregation processor.

This module performs spatial joins to aggregate point data (Airbnb, STR, etc.)
to census tract level with count and density calculations.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class PointsToTractProcessor(DataProcessor):
    """Aggregate point data to census tracts.

    This processor:
    1. Performs spatial join (points → tracts)
    2. Aggregates by tract (count, averages, etc.)
    3. Calculates densities per km²
    4. Returns tract-level GeoDataFrame

    Example use cases:
    - Airbnb listings per tract
    - STR prohibition zones per tract
    - Crime incidents per tract
    - Building violations per tract
    """

    def __init__(
        self,
        input_key: str = "point_data",
        output_key: str = "tract_aggregated_data",
        id_column: str | None = None,
        aggregate_columns: dict[str, str | list[str]] | None = None,
        calculate_density: bool = True,
        data_source_name: str | None = None,
    ) -> None:
        """Initialize the points to tract processor.

        Args:
            input_key: Context key for input point data (GeoDataFrame)
            output_key: Context key for output tract data
            id_column: Column to count (if None, counts all rows)
            aggregate_columns: Dict of {column: aggregation} for additional stats
                              e.g., {"price": "mean"} or {"price": ["mean", "median"]}
            calculate_density: Whether to calculate points per km²
            data_source_name: Prefix for column names (e.g., "airbnb", "str_prohibition")
        """
        super().__init__(
            f"points_to_tract_{input_key}",
            f"Aggregate {input_key} point data to census tracts",
        )
        self.input_key = input_key
        self.output_key = output_key
        self.id_column = id_column
        self.aggregate_columns = aggregate_columns or {}
        self.calculate_density = calculate_density

        # Set data source name - use input_key if not provided
        if data_source_name is None:
            # Extract meaningful name from input_key (e.g., "airbnb_data" -> "airbnb")
            self.data_source_name = input_key.replace("_data", "")
        else:
            self.data_source_name = data_source_name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation."""
        # Get data from context
        point_data = context[self.input_key]
        tract_boundaries = context["tract_boundaries"]

        # Step 1: Ensure both datasets are in same CRS
        if point_data.crs != tract_boundaries.crs:
            point_data = point_data.to_crs(tract_boundaries.crs)

        # Step 2: Spatial join - which tract is each point in?
        points_with_tract = gpd.sjoin(
            point_data,
            tract_boundaries[["tract_geoid", "geometry"]],
            how="left",
            predicate="within",
        )

        # Step 3: Aggregate by tract

        # Build aggregation dictionary
        agg_dict = {}

        # Count points (use id_column if specified, otherwise count rows)
        if self.id_column:
            agg_dict[self.id_column] = "count"
        else:
            # Use first available column for counting
            agg_dict[points_with_tract.columns[0]] = "count"

        # Add custom aggregations
        agg_dict.update(self.aggregate_columns)

        # Perform aggregation
        tract_agg = points_with_tract.groupby("tract_geoid").agg(agg_dict).reset_index()

        # Flatten MultiIndex columns if they exist
        if isinstance(tract_agg.columns, pd.MultiIndex):
            tract_agg.columns = [
                "_".join(col).strip() if col[1] else col[0]
                for col in tract_agg.columns.to_numpy()
            ]

        # Rename count column with data source prefix
        count_col = self.id_column or points_with_tract.columns[0]
        count_col_name = (
            f"{count_col}_count"
            if f"{count_col}_count" in tract_agg.columns
            else count_col
        )
        tract_agg = tract_agg.rename(
            columns={count_col_name: f"{self.data_source_name}_count"}
        )

        # Step 4: Join with tract geometries
        tract_data = tract_boundaries[["tract_geoid", "geometry"]].merge(
            tract_agg, on="tract_geoid", how="left"
        )

        # Fill NaN counts with 0 (tracts with no points)
        count_column_name = f"{self.data_source_name}_count"
        tract_data[count_column_name] = tract_data[count_column_name].fillna(0)

        # Step 5: Calculate density if requested
        if self.calculate_density:
            # Convert to projected CRS for accurate area calculation
            tract_projected = tract_data.to_crs("EPSG:32616")  # UTM Zone 16N
            tract_projected["area_km2"] = tract_projected.geometry.area / 1_000_000

            # Calculate density
            density_column_name = f"{self.data_source_name}_density"
            tract_projected[density_column_name] = (
                tract_projected[count_column_name] / tract_projected["area_km2"]
            )

            # Copy calculated columns back to original CRS
            tract_data["area_km2"] = tract_projected["area_km2"].to_numpy()
            tract_data[density_column_name] = tract_projected[
                density_column_name
            ].to_numpy()

        # Convert to GeoDataFrame
        tract_data = gpd.GeoDataFrame(
            tract_data, geometry="geometry", crs=tract_boundaries.crs
        )

        return {
            self.output_key: tract_data,
            f"{self.output_key}_summary": {
                "total_tracts": len(tract_data),
                "tracts_with_points": (tract_data[count_column_name] > 0).sum(),
                "total_points": int(tract_data[count_column_name].sum()),
                "avg_points_per_tract": float(tract_data[count_column_name].mean()),
                "max_points_per_tract": int(tract_data[count_column_name].max()),
            },
        }


class AirbnbToTractProcessor(PointsToTractProcessor):
    """Convenience class for Airbnb listings → tracts aggregation."""

    def __init__(
        self,
        input_key: str = "airbnb_data",
        output_key: str = "airbnb_tract_data",
        id_column: str = "id",
        price_column: str = "price",
    ) -> None:
        """Initialize Airbnb to tract processor.

        Args:
            input_key: Context key for Airbnb point data
            output_key: Context key for output tract data
            id_column: Column with listing IDs
            price_column: Column with listing prices
        """
        super().__init__(
            input_key=input_key,
            output_key=output_key,
            id_column=id_column,
            aggregate_columns={
                price_column: ["mean", "median", "min", "max"],
            },
            calculate_density=True,
            data_source_name="airbnb",
        )
