"""STR units density map visualizer.

This module creates side-by-side choropleth maps showing STR units density
distributions at both the tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt

from housing.components.utils import create_choropleth_map, prepare_map_data
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRUnitsDensityMaps(Visualizer):
    """Create side-by-side choropleth maps for STR units density."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR units density map visualizer."""
        super().__init__(
            "str_units_density_maps_visualization",
            "Create side-by-side choropleth maps for STR units density",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR units density visualizations for tract and community levels."""
        logger.info("Creating STR units density maps (tract and community)...")

        tract_data = context.get("str_units_tract_data")
        community_data = context.get("str_units_community_data")
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None or tract_boundaries is None:
            logger.warning("No STR tract data or boundaries available for mapping")
            return {}

        if community_data is None or community_boundaries is None:
            logger.warning("No STR community data or boundaries available for mapping")
            return {}

        # Prepare tract map data
        tract_map_data = prepare_map_data(
            tract_data,
            tract_boundaries,
            ["str_units_density"],
            city_boundaries,
            logger=logger,
        )

        # Prepare community map data
        community_map_data = community_boundaries.merge(
            community_data[["community_name", "str_units_density"]],
            on="community_name",
            how="left",
        )

        # Clip both datasets to city boundaries
        if city_boundaries is not None:
            if tract_map_data.crs != city_boundaries.crs:
                city_boundaries = city_boundaries.to_crs(tract_map_data.crs)
            tract_map_data = gpd.clip(tract_map_data, city_boundaries)
            community_map_data = gpd.clip(community_map_data, city_boundaries)
            logger.info(
                "Clipped both tract and community data to Chicago city boundaries"
            )

        common_bounds = (
            city_boundaries.total_bounds if city_boundaries is not None else None
        )

        # Create figure
        fig, axes = plt.subplots(1, 2, figsize=(15, 10))

        # Tract Density
        create_choropleth_map(
            ax=axes[0],
            map_data=tract_map_data,
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

        # Community Density
        create_choropleth_map(
            ax=axes[1],
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
        output_path = Path(self.output_dir) / "str_units_density_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved STR units density maps to: %s", output_path)
        plt.close()

        return {"str_units_density_maps": str(output_path)}
