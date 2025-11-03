"""STR units map visualizer.

This module creates choropleth maps showing STR units count and density
distributions at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt

from housing.components.utils import create_choropleth_map, prepare_map_data
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRUnitsMapVisualizer(Visualizer):
    """Create choropleth maps for STR units data."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR units map visualizer."""
        super().__init__(
            "str_map_visualization",
            "Create choropleth maps for STR units data",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR units map visualizations."""
        logger.info("Creating STR units map visualizations...")

        tract_data = context.get("str_units_tract_data")
        community_data = context.get("str_units_community_data")
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None and community_data is None:
            logger.warning("No STR data available for mapping")
            return {}

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(
            "Chicago Short-Term Rentals: Units Count & Density",
            fontsize=20,
            fontweight="bold",
            y=0.98,
        )

        common_bounds = (
            city_boundaries.total_bounds if city_boundaries is not None else None
        )

        # Tract Level
        if tract_data is not None and tract_boundaries is not None:
            map_data = prepare_map_data(
                tract_data,
                tract_boundaries,
                ["str_units_count", "str_units_density"],
                city_boundaries,
                logger=logger,
            )

            # Clip tract data to city boundaries
            if city_boundaries is not None:
                if map_data.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(map_data.crs)
                map_data = gpd.clip(map_data, city_boundaries)
                logger.info("Clipped tract data to Chicago city boundaries")

            # Count
            create_choropleth_map(
                ax=axes[0, 0],
                map_data=map_data,
                column="str_units_count",
                title="STR Units Count (Tract Level)",
                legend_label="STR Units Count",
                cmap="YlOrRd",
                bounds=common_bounds,
                edge_color="black",
                edge_width=0.1,
                stats_format="{:.0f}",
                logger=logger,
            )

            # Density
            create_choropleth_map(
                ax=axes[0, 1],
                map_data=map_data,
                column="str_units_density",
                title="STR Units Density (Tract Level)",
                legend_label="STR Units Density (per km²)",
                cmap="YlOrRd",
                bounds=common_bounds,
                edge_color="black",
                edge_width=0.1,
                stats_format="{:.2f}",
                logger=logger,
            )

        # Community Level Maps
        if community_data is not None and community_boundaries is not None:
            community_map_data = community_boundaries.merge(
                community_data[
                    ["community_name", "str_units_count", "str_units_density"]
                ],
                on="community_name",
                how="left",
            )

            if city_boundaries is not None:
                if community_map_data.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(community_map_data.crs)
                community_map_data = gpd.clip(community_map_data, city_boundaries)
                logger.info("Clipped community data to Chicago city boundaries")

            # Count
            create_choropleth_map(
                ax=axes[1, 0],
                map_data=community_map_data,
                column="str_units_count",
                title="STR Units Count (Community Level)",
                legend_label="STR Units Count",
                cmap="YlOrRd",
                bounds=common_bounds,
                edge_color="black",
                edge_width=0.1,
                stats_format="{:.0f}",
                logger=logger,
            )

            # Community: Units Density
            create_choropleth_map(
                ax=axes[1, 1],
                map_data=community_map_data,
                column="str_units_density",
                title="STR Units Density (Community Level)",
                legend_label="STR Units Density (per km²)",
                cmap="YlOrRd",
                bounds=common_bounds,
                edge_color="black",
                edge_width=0.1,
                stats_format="{:.2f}",
                logger=logger,
            )

        # Save output
        output_path = Path(self.output_dir) / "str_units_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)
        plt.close()

        return {"str_units_map_plot": str(output_path)}
