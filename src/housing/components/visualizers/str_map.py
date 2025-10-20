"""STR prohibition map visualizer.

This module creates choropleth maps showing STR prohibition distributions
at census tract level.
"""

import logging
from pathlib import Path
from typing import Any

from housing.components.utils import create_dual_choropleth_maps, setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRMapVisualizer(Visualizer):
    """Create choropleth maps for STR prohibitions.

    Shows STR prohibition data as geographic maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_map_visualization",
            "Create choropleth maps for STR prohibitions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR prohibition map visualizations."""
        logger.info("Creating STR prohibition map visualizations...")

        tract_data = context.get("str_tract_analysis")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None:
            logger.warning("No STR tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Define map configurations
        map_configs = []

        # Add STR prohibition density map if available
        if "str_prohibition_density" in tract_data.columns:
            map_configs.append(
                {
                    "column": "str_prohibition_density",
                    "title": "STR Units Density",
                    "legend_label": "STR Units Density (per km²)",
                    "cmap": "YlOrRd",  # Yellow to red gradient
                    "stats_format": "{:.1f}",
                }
            )

        # Add building density map if available (calculate on the fly)
        if (
            "str_prohibition_count" in tract_data.columns
            and "area_km2" in tract_data.columns
        ):
            # Calculate building density
            tract_data = tract_data.copy()
            tract_data["building_density"] = (
                tract_data["str_prohibition_count"] / tract_data["area_km2"]
            )

            map_configs.append(
                {
                    "column": "building_density",
                    "title": "STR Buildings Density",
                    "legend_label": "STR Buildings Density (per km²)",
                    "cmap": "Oranges",
                    "stats_format": "{:.1f}",
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
            figsize=(22, 10),
            title="Chicago STR Prohibition Analysis by Census Tract",
            logger=logger,
        )

        # Save the plot
        output_path = Path(self.output_dir) / "str_density_maps.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="Chicago STR Prohibition Analysis by Census Tract",
            logger=logger,
        )

        return {"str_map_plot": str(output_path)}
