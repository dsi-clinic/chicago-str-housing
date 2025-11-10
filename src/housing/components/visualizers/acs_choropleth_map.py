"""ACS Choropleth Map.

This module creates choropleth map  for ACS results.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd

from housing.components.utils import (
    create_choropleth_maps,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class ACSChoroplethVisualizer(Visualizer):
    """Create choropleth maps for the tract acs data"""

    def __init__(
        self,
        input_key: str | None = None,
        output_dir: str | None = None,
        scheme: str | None = None,
    ) -> None:
        """Initialize the ACS map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "acs_map_visualization",
            "Create choropleth maps for the tract ACS",
        )
        self.input_key = input_key
        self.scheme = scheme or "Quantiles"
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create tract acs choropleth map ."""
        logger.info("Creating tract acs choropleth...")
        logger.info("Step 1: Loading Data...")

        # tract_data = context[self.input_key]
        tract_data = gpd.read_file(self.input_key)
        eda_tract_data = context["acs_tract_data"]
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None:
            logger.warning("No Airbnb tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Adding poverty status to full gpd
        tract_data = tract_data.merge(
            eda_tract_data[["tract_geoid", "below_50_poverty_density"]],
            left_on="tract_id",
            right_on="tract_geoid",
            how="left",
        )

        census_variables = [
            "population_density",
            "below_50_poverty_density",
            "census_median_income",
            "census_median_house_value",
            "census_median_age",
            "census_pct_bachelor",
            "census_pct_rented",
        ]

        # Clip to city boundaries if available
        if city_boundaries is not None:
            # Ensure same CRS
            if tract_data.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tract_data.crs)
                # Clip community areas to city boundary
        tract_map_data = gpd.clip(tract_data, city_boundaries)

        # Creating CHoropleth Map
        output_path = Path(self.output_dir) / "acs_choropleth_maps.png"
        logger.info("Step 2: Creating tract acs choropleth...")
        create_choropleth_maps(
            tract_map_data,
            census_variables,
            output_path=output_path,
            scheme=self.scheme,
            cmap="YlOrRd",
        )

        return {"acs_choropleht_map": str(output_path)}
