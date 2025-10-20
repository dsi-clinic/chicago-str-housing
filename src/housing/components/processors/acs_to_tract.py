"""ACS Data to census tract processor.

This module performs traditional joins (with shapefile) with count and density calculations.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class ACSToTractProcessor(DataProcessor):
    """Perform merge join between acs  data and tracts boundries on GEOID.

     This processor:
    1. Performs traditiona join (tracts → tracts with boundaries)
    2. Calculates densities per km²
    3. Returns tract-level GeoDataFrame
    """

    def __init__(
        self,
        input_key: str = "acs_data",
        output_key: str = "acs_tract_data",
        id_column: str | None = None,
        aggregate_columns: dict[str, str | list[str]] | None = None,
        calculate_density: bool = True,
    ) -> None:
        super().__init__(
            "acs_to_tract",
            "merge acs data with tract boundaries",
        )
        self.input_key = input_key
        self.output_key = output_key
        self.id_column = id_column
        self.aggregate_columns = aggregate_columns or {}
        self.calculate_density = calculate_density

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform traditional join and aggregation."""
        logger.info("Merging %s with tract boundaries...", self.input_key)
        logger.info("Performing attributed join: acs data -> acs data with boundaries")

        # Get the data from context
        acs_data = context[self.input_key]
        tract_boundaries = context["tract_boundaries"]

        logger.info("Column Names: %s", tract_boundaries.columns.to_list())
        logger.info("Load %d ACS data", len(tract_boundaries))

        # Step 1: Traditional join - Connect each data with its corresponding tract boundaries
        logger.info("Step 1: Traditional join (tracts → tracts + boundaries)...")

        acs_with_tract = tract_boundaries[["GEOID", "tract_geoid", "geometry"]].merge(
            acs_data, on="GEOID", how="inner"
        )

        logger.info("Load %d census tract with ACS data", len(acs_with_tract))

        # Step 2: Calculate density if requested
        if self.calculate_density:
            logger.info("Step 2: Calculating point density per km²...")

            # Convert to projected CRS for accurate area calculation
            tract_projected = acs_with_tract.to_crs("EPSG:32616")  # UTM Zone 16N
            tract_projected["area_km2"] = tract_projected.geometry.area / 1_000_000

            # Calculate density & copy calculated columns back to original CRS
            numeric_cols = [
                "population",
                "median_house_income",
                "total_house_built",
                "total_tenure",
                "total_transportation",
            ]
            acs_with_tract = self.calculate_density_area(
                numeric_cols, tract_projected, acs_with_tract
            )

            # Copy calculated area_km2 back to original CRS
            acs_with_tract["area_km2"] = tract_projected["area_km2"].to_numpy()

            logger.info("Column Names: %s", acs_with_tract.columns.to_list())
        # Step 3: Convert to GeoDataFrame
        logger.info("Step 2: Calculating point density per km²...")
        acs_with_tract = gpd.GeoDataFrame(
            acs_with_tract, geometry="geometry", crs=tract_boundaries.crs
        )

        return {
            self.output_key: acs_with_tract,
            f"{self.output_key}_summary": {
                "total_tracts": len(acs_with_tract),
                "avg_pop_per_tract": (acs_with_tract["population_density"].mean()),
                "avg_median_income_per_tract": (
                    acs_with_tract["median_house_income_density"].mean()
                ),
                "avg_house_built_per_tract": (
                    acs_with_tract["total_house_built_density"].mean()
                ),
                "avg_tenure_per_tract": (acs_with_tract["total_tenure_density"].mean()),
                "avg_transport_per_tract": (
                    acs_with_tract["total_transportation_density"].mean()
                ),
            },
        }

    def calculate_density_area(
        self,
        variable_list: list,
        tract_projected: pd.DataFrame,
        acs_with_tract: pd.DataFrame,
    ) -> pd.DataFrame:
        """Helper function to create the density for each variable"""
        for var in variable_list:
            tract_projected[f"{var}_density"] = (
                tract_projected[var] / tract_projected["area_km2"]
            )
            acs_with_tract[f"{var}_density"] = tract_projected[
                f"{var}_density"
            ].to_numpy()

        return acs_with_tract
