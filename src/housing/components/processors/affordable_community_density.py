"""Point data to community area aggregation processor.

This module performs spatial joins to aggregate point data (Airbnb, STR, etc.)
to community area level with count and density calculations.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class AffordableToCommunityProcessor(DataProcessor):
    """Aggregate point data to community areas.

    This processor:
    1. Performs spatial join (points → communities)
    2. Aggregates by community area (count, averages, etc.)
    3. Calculates densities per km²
    4. Returns community-level GeoDataFrame
    """

    def __init__(
        self,
        input_key: str = "affordable_development_data",
        output_key: str = "affordable_development_community_data",
        id_column: str | None = None,
        aggregate_columns: dict[str, str | list[str]] | None = None,
        calculate_density: bool = True,
        data_source_name: str | None = "affordable_development",
        unit_column: str | None = "units",
    ) -> None:
        """Initialize the points to community area processor.

        Args:
            input_key: Context key for input point data (GeoDataFrame)
            output_key: Context key for output community-level data
            id_column: Column to count (if None, counts all rows)
            aggregate_columns: Dict of {column: aggregation} for additional stats
                              e.g., {"price": "mean"} or {"price": ["mean", "median"]}
            calculate_density: Whether to calculate points per km²
            data_source_name: Prefix for column names (e.g., "airbnb", "str_prohibition")
            unit_column: The name of the column in the input where unit data is stored
        """
        super().__init__(
            f"points_to_community_{input_key}",
            f"Aggregate {input_key} point data to community area",
        )
        self.input_key = input_key
        self.output_key = output_key
        self.id_column = id_column
        self.aggregate_columns = aggregate_columns or {
            "units": ["sum", "mean", "median"]
        }
        self.calculate_density = calculate_density
        self.unit_column = unit_column

        # Set data source name - use input_key if not provided
        if data_source_name is None:
            # Extract meaningful name from input_key (e.g., "airbnb_data" -> "airbnb")
            self.data_source_name = input_key.replace("_data", "").replace("_", "_")
        else:
            self.data_source_name = data_source_name

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform spatial join and aggregation."""
        logger.info("Aggregating %s point data to community areas...", self.input_key)

        # Get data from context
        point_data = context[self.input_key]
        community_boundaries = context["community_boundaries"]

        # remove confusing community_area column from point data
        point_data = point_data.drop("community_area", axis=1)

        # ensure columns to merge on are the same datatype
        boundary_numbers_type = community_boundaries["community_area"].dtype
        point_numbers_type = point_data["community_area_number"].dtype

        if boundary_numbers_type != point_numbers_type:
            point_data["community_area_number"] = point_data[
                "community_area_number"
            ].astype(int)
            community_boundaries["community_area"] = community_boundaries[
                "community_area"
            ].astype(int)

        # Step 1: Ensure both datasets are in same CRS
        logger.info("Step 1: Aligning coordinate systems...")
        if point_data.crs != community_boundaries.crs:
            point_data = point_data.to_crs(community_boundaries.crs)

        # Step 2: Spatial join - which community area is each point in?
        logger.info("Step 2: Spatial join (points → communities)...")
        points_with_community = gpd.sjoin(
            point_data,
            community_boundaries[["community_area", "community_name", "geometry"]],
            how="left",
            predicate="within",
        )

        # Log statistics
        total_points = len(points_with_community)
        matched_points = points_with_community["community_area"].notna().sum()
        logger.info(
            "Matched %d/%d points to community areas (%.1f%%)",
            matched_points,
            total_points,
            100 * matched_points / total_points if total_points > 0 else 0,
        )

        # Step 3: Aggregate by community area
        logger.info("Step 3: Aggregating by community area...")

        # Build aggregation dictionary
        agg_dict = {}

        # Count points (use id_column if specified, otherwise count rows)
        if self.id_column:
            agg_dict[self.id_column] = "count"
        else:
            # Use first available column for counting
            agg_dict[points_with_community.columns[0]] = "count"

        # Add custom aggregations
        agg_dict.update(self.aggregate_columns)

        # Perform aggregation
        community_agg = (
            points_with_community.groupby("community_area").agg(agg_dict).reset_index()
        )

        # Flatten MultiIndex columns if they exist
        if isinstance(community_agg.columns, pd.MultiIndex):
            community_agg.columns = [
                "_".join(col).strip() if col[1] else col[0]
                for col in community_agg.columns.to_numpy()
            ]

        # Rename count column with data source prefix
        count_col = self.id_column or points_with_community.columns[0]
        count_col_name = (
            f"{count_col}_count"
            if f"{count_col}_count" in community_agg.columns
            else count_col
        )
        community_agg = community_agg.rename(
            columns={count_col_name: f"{self.data_source_name}_count"}
        )

        logger.info("Aggregated to %d community areas", len(community_agg))

        # Step 4: Join with community area geometries
        logger.info("Step 4: Joining with community area geometries...")
        community_data = community_boundaries[
            ["community_area", "community_name", "geometry"]
        ].merge(community_agg, on="community_area", how="left")

        # Fill NaN counts with 0 (communities with no points)
        count_column_name = f"{self.data_source_name}_count"
        community_data[count_column_name] = community_data[count_column_name].fillna(0)

        # Step 5: Calculate density if requested
        if self.calculate_density:
            logger.info("Step 5: Calculating point density per km²...")

            # Convert to projected CRS for accurate area calculation
            community_projected = community_data.to_crs("EPSG:32616")  # UTM Zone 16N
            community_projected["area_km2"] = (
                community_projected.geometry.area / 1_000_000
            )

            # Calculate density
            density_column_name = f"{self.data_source_name}_density"
            community_projected[density_column_name] = (
                community_projected[count_column_name] / community_projected["area_km2"]
            )

            # Copy calculated columns back to original CRS
            community_data["area_km2"] = community_projected["area_km2"].to_numpy()
            community_data[density_column_name] = community_projected[
                density_column_name
            ].to_numpy()

            logger.info(
                "Density range: %.2f - %.2f points/km²",
                community_data[density_column_name].min(),
                community_data[density_column_name].max(),
            )

            if f"{self.unit_column}_sum" in community_data.columns:
                community_data[f"{self.data_source_name}_unit_density"] = (
                    community_data[f"{self.unit_column}_sum"]
                    / community_data["area_km2"]
                )
                community_data[f"{self.data_source_name}_unit_density"] = (
                    community_data[f"{self.data_source_name}_unit_density"].fillna(0)
                )
                logger.info(
                    "Calculated unit density range: %.2f - %.2f units/km²",
                    community_data[f"{self.data_source_name}_unit_density"].min(),
                    community_data[f"{self.data_source_name}_unit_density"].max(),
                )
            else:
                logger.warning(
                    "Column %s not found in tract data", f"{self.unit_column}_sum"
                )

        # Convert to GeoDataFrame
        community_data = gpd.GeoDataFrame(
            community_data, geometry="geometry", crs=community_boundaries.crs
        )

        # Log summary statistics
        logger.info(
            "Summary: %d communities total, %d with points (%.1f%%)",
            len(community_data),
            (community_data[count_column_name] > 0).sum(),
            100 * (community_data[count_column_name] > 0).sum() / len(community_data)
            if len(community_data) > 0
            else 0,
        )

        return {
            self.output_key: community_data,
            f"{self.output_key}_summary": {
                "total_communities": len(community_data),
                "communities_with_points": (
                    community_data[count_column_name] > 0
                ).sum(),
                "total_points": int(community_data[count_column_name].sum()),
                "avg_points_per_community": float(
                    community_data[count_column_name].mean()
                ),
                "max_points_per_community": int(
                    community_data[count_column_name].max()
                ),
            },
        }
