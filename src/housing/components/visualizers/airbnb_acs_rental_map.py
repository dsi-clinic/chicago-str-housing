"""Income and House price map visualizer.

This module creates choropleth maps showing Airbnb, ACS, and Rental price distributions
at census tract level.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    create_choropleth_map,
    prepare_map_data,
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class IncomePriceMapVisualizer(Visualizer):
    """Create choropleth maps for Airbnb prices.

    Shows Airbnb, ACS, and Rental prices as geographic maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the Airbnb map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "airbnb_acs_remtal_map_visualization",
            "Create choropleth maps for Airbnb, ACS, and Rental prices",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create Airbnb, ACS, and Rental price map visualizations."""
        logger.info("Creating Airbnb, ACS, and Rental price map visualizations...")

        airbnb_tract_data = context.get("airbnb_tract_data")
        acs_tract_data = context.get("acs_tract_data")
        rental_tract_data = context.get("tract_rental_data")

        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if airbnb_tract_data is None:
            logger.warning("No Airbnb tract data available for mapping")
            return {}

        if acs_tract_data is None:
            logger.warning("No ACS tract data available for mapping")
            return {}

        if rental_tract_data is None:
            logger.warning("No Rental tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Define map configurations
        map_configs = []

        if "median_house_income" in acs_tract_data.columns:
            acs_tract_data["monthly_income"] = (
                acs_tract_data["median_house_income"] / 12
            )
            map_configs.append(
                {
                    "column": "monthly_income",
                    "title": "Monthly Household Income Distribution",
                    "legend_label": "Average Monthly Income ($)",
                    "cmap": "YlOrRd",
                    "stats_format": "${:.0f}",
                }
            )

        if "price_numeric_mean" in airbnb_tract_data.columns:
            airbnb_tract_data["monthly_airbnb_price"] = (
                airbnb_tract_data["price_numeric_mean"] * 30
            )

            map_configs.append(
                {
                    "column": "price_numeric_mean",
                    # "column": "monthly_airbnb_price",
                    "title": "Airbnb Price Distribution",
                    "legend_label": "Average Monthly Airbnb Price ($)",
                    "cmap": "YlOrRd",
                    "stats_format": "${:.0f}",
                }
            )

        if "avg_rental_price" in rental_tract_data.columns:
            map_configs.append(
                {
                    "column": "avg_rental_price",
                    "title": "Zori Rental Distribution",
                    "legend_label": "Average Rental Price ($)",
                    "cmap": "YlOrRd",
                    "stats_format": "{:.1f} units/km²",
                }
            )

        if not map_configs:
            logger.warning("No valid data columns found for mapping")
            return {}

        # Create figure
        fig, axes = plt.subplots(1, 3, figsize=(20, 10))
        fig.suptitle("Choropleth Analysis", fontsize=20, fontweight="bold", y=0.98)

        # Get common bounds for consistent zoom
        if city_boundaries is not None:
            common_bounds = city_boundaries.total_bounds
        else:
            common_bounds = tract_boundaries.total_bounds

        # Create each map
        dataframe = [acs_tract_data, airbnb_tract_data, rental_tract_data]
        for i, config in enumerate(map_configs):
            # Prepare data for this map
            data_columns = [config["column"]]
            map_data = prepare_map_data(
                dataframe[i],
                tract_boundaries,
                data_columns,
                city_boundaries,
                logger=logger,
            )

            # Create the choropleth map
            create_choropleth_map(
                axes[i],
                map_data,
                config["column"],
                config["title"],
                config["legend_label"],
                cmap=config.get("cmap", "YlOrRd"),
                bounds=common_bounds,
                show_stats=config.get("show_stats", True),
                stats_format=config.get("stats_format", "${:.0f}"),
                logger=logger,
            )

        # Save the plot
        output_path = Path(self.output_dir) / "airbnb_acs_rental_maps.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="Chicago Income and Cost Analysis per Month by Census Tract",
            logger=logger,
        )

        return {"airbnb_acs_rental_maps": str(output_path)}
