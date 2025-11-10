"""ACS Pertinent Choropleth Map.

This module creates pertinent choropleth map  for ACS results.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt

from housing.components.utils import (
    prepare_map_data,
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class ACSChoroplethPlotVisualizer(Visualizer):
    """Create pertinent choropleth maps for the tract acs data"""

    def __init__(
        self,
        input_key: str | None = None,
        output_dir: str | None = None,
        scheme: str | None = None,
    ) -> None:
        """Initialize the ACS map visualizer.

        Args:
            input_key: Context key for input point data (GeoDataFrame)
            output_dir: Optional output directory for visualizations
            scheme: type of scheme for choropleth map
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
        logger.info("Creating pertinent tract acs choropleth...")
        logger.info("Step 1: Loading Data...")

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
            "below_50_poverty_density",
            "census_median_income",
            "census_median_house_value",
            "census_median_age",
            "census_pct_bachelor",
        ]

        # Clip to city boundaries if available
        if city_boundaries is not None:
            # Ensure same CRS
            if tract_data.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tract_data.crs)
                # Clip community areas to city boundary

        tract_map_data = gpd.clip(tract_data, city_boundaries)

        tract_map_data = tract_map_data.dropna()

        # Customize the titles
        custom_titles = [
            "Below 50% Poverty Density",
            "Median Income",
            "Median House Value",
            "Median Age",
            "Percent Bachelor Degree",
        ]

        logger.info("Step 2: Creating Choropleth Maps...")
        # Create figure
        fig, axes = plt.subplots(1, len(census_variables), figsize=(25, 7))
        axes.flatten()

        # Create Choropleth Map
        for i, col_var in enumerate(census_variables):
            map_data = prepare_map_data(
                tract_map_data,
                tract_boundaries,
                census_variables,
                city_boundaries,
                logger=logger,
            )

            map_data.plot(
                column=col_var,
                ax=axes[i],
                scheme=self.scheme,
                k=5,
                linewidth=0.1,
                edgecolor="black",
                cmap="YlOrRd",
                legend=True,
                legend_kwds={"loc": "lower left"},
            )

            axes[i].set_title(custom_titles[i])
            axes[i].set_axis_off()

            plt.tight_layout()

        # Creating CHoropleth Map
        output_path = Path(self.output_dir) / "acs_choropleth_maps_fisherjenks.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="Census Data Choropleth Map using FisherJenks",
            logger=logger,
        )

        return {"acs_choropleht_map": str(output_path)}
