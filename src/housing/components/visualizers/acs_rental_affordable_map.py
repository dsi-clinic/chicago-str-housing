"""Affordable Income and House price map visualizer.

This module creates choropleth maps showing whether census tract is affordable base on
ACS, and Rental price at census tract level.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    create_choropleth_map,
    create_histogram_with_median,
    prepare_map_data,
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class AffordableMapVisualizer(Visualizer):
    """Create choropleth maps for Airbnb prices.

    Shows Airbnb, ACS, and Rental prices as geographic maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the Afforadable map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "acs_rental_affordable_map_visualization",
            "Create choropleth maps for Affordability",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create affordability map visualizations."""
        logger.info("Creating affordability map visualizations...")

        acs_tract_data = context.get("acs_tract_data")
        rental_tract_data = context.get("tract_rental_data")

        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if acs_tract_data is None:
            logger.warning("No ACS tract data available for mapping")
            return {}

        if rental_tract_data is None:
            logger.warning("No Rental tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Create 30% Monthly Income
        acs_tract_data["monthly_income30"] = (
            acs_tract_data["median_house_income"] / 12 * 0.3
        )  # 30% of income

        acs_rental_data = acs_tract_data.merge(
            rental_tract_data, how="inner", on="tract_geoid"
        )

        # Create Difference between 30% Monthly income and Rental Price
        acs_rental_data["afford_diff"] = (
            acs_rental_data["monthly_income30"] - acs_rental_data["avg_rental_price"]
        )

        # Define map configurations
        map_configs = []

        if (
            "median_house_income" in acs_tract_data.columns
            and "avg_rental_price" in rental_tract_data.columns
        ):
            map_configs.append(
                {
                    "column": "afford_diff",
                    "title": "Difference in 30% of Monthly Household Income and Rental Price (Affordability)",
                    "legend_label": "Average Monthly Income ($)",
                    "cmap": "RdYlGn",
                    "stats_format": "${:.0f}",
                }
            )

        if not map_configs:
            logger.warning("No valid data columns found for mapping")
            return {}

        # Create figure
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle("Choropleth Analysis", fontsize=20, fontweight="bold", y=0.98)

        # Get common bounds for consistent zoom
        if city_boundaries is not None:
            common_bounds = city_boundaries.total_bounds
        else:
            common_bounds = tract_boundaries.total_bounds

        # Create each map
        dataframe = [acs_rental_data]
        config = map_configs[0]
        # for i, config in enumerate(map_configs):
        # Prepare data for this map
        data_columns = [config["column"]]
        map_data = prepare_map_data(
            dataframe[0],
            tract_boundaries,
            data_columns,
            city_boundaries,
            logger=logger,
        )

        # Create the choropleth map
        create_choropleth_map(
            axes[0],
            map_data,
            config["column"],
            config["title"],
            config["legend_label"],
            cmap=config.get("cmap", "RdYlGn"),
            bounds=common_bounds,
            show_stats=config.get("show_stats", True),
            stats_format=config.get("stats_format", "${:.0f}"),
            logger=logger,
        )

        # Distribution of Difference in 30% Income and Rental Price
        if acs_rental_data is not None:
            create_histogram_with_median(
                axes[1],
                acs_rental_data["afford_diff"],
                "Census Tract Level",
                "Affordability Price Differences ($)",
                "Number of Census Tracts",
                color="steelblue",
                median_format="${:.0f}",
            )
        # Save the plot
        output_path = Path(self.output_dir) / "acs_rental_affordable_maps.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="Chicago Affordability by Census Tract",
            logger=logger,
        )

        return {"acs_rental_affordable_maps": str(output_path)}
