"""Airbnb price map visualizer.

This module creates choropleth maps showing Airbnb price distributions
at census tract level.
"""

import logging
from pathlib import Path
from typing import Any

from housing.components.utils import create_dual_choropleth_maps, setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class AirbnbMapVisualizer(Visualizer):
    """Create choropleth maps for Airbnb prices.

    Shows Airbnb prices as geographic maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the Airbnb map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "airbnb_map_visualization",
            "Create choropleth maps for Airbnb prices",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create Airbnb price map visualizations."""
        logger.info("Creating Airbnb price map visualizations...")

        tract_data = context.get("airbnb_tract_data")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None:
            logger.warning("No Airbnb tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Define map configurations
        map_configs = []

        if "price_numeric_mean" in tract_data.columns:
            map_configs.append(
                {
                    "column": "price_numeric_mean",
                    "title": "Airbnb Price Distribution",
                    "legend_label": "Average Airbnb Price ($)",
                    "cmap": "viridis",
                    "stats_format": "${:.0f}",
                }
            )

        if "point_density" in tract_data.columns:
            map_configs.append(
                {
                    "column": "point_density",
                    "title": "Airbnb Units Density Distribution",
                    "legend_label": "Airbnb Units Density (per km²)",
                    "cmap": "Blues",
                    "stats_format": "{:.1f} units/km²",
                }
            )

        if not map_configs:
            logger.warning("No valid data columns found for mapping")
            return {}

        # Create dual choropleth maps
        fig, axes = create_dual_choropleth_maps(
            tract_data,
            tract_boundaries,
            map_configs,
            city_boundaries,
            figsize=(20, 10),
            title="Chicago Airbnb Analysis by Census Tract",
            logger=logger,
        )

        # Save the plot
        output_path = Path(self.output_dir) / "airbnb_analysis_maps.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="Chicago Airbnb Analysis by Census Tract",
            logger=logger,
        )

        return {"airbnb_map_plot": str(output_path)}
