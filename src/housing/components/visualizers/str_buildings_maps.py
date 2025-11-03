"""STR buildings map visualizer.

This module creates choropleth maps showing STR buildings count and density
distributions at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRBuildingsMapVisualizer(Visualizer):
    """Create choropleth maps for STR buildings data.

    Shows STR buildings count and density as geographic maps at both census tract
    and community area levels.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR buildings map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_map_visualization",
            "Create choropleth maps for STR buildings data",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR buildings map visualizations."""
        logger.info("Creating STR buildings map visualizations...")

        tract_data = context.get("str_buildings_tract_data")
        community_data = context.get("str_buildings_community_data")
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None and community_data is None:
            logger.warning("No STR data available for mapping")
            return {}

        # Create figure with 2x2 subplots
        fig, axes = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle(
            "Chicago Short-Term Rentals: Buildings Count & Density",
            fontsize=20,
            fontweight="bold",
            y=0.98,
        )

        # Common city bounds
        common_bounds = (
            city_boundaries.total_bounds if city_boundaries is not None else None
        )

        import geopandas as gpd

        from housing.components.utils import create_choropleth_map, prepare_map_data

        # --------- 1. Census Tract Level Maps ---------
        if tract_data is not None and tract_boundaries is not None:
            map_data = prepare_map_data(
                tract_data,
                tract_boundaries,
                ["str_buildings_count", "str_buildings_density"],
                city_boundaries,
                logger=logger,
            )

            # Count
            create_choropleth_map(
                axes[0, 0],
                map_data,
                "str_buildings_count",
                "Census Tract Level",
                "STR Buildings Count",
                cmap="YlOrRd",
                bounds=common_bounds,
                stats_format="{:.0f}",
                logger=logger,
            )

            # Density
            create_choropleth_map(
                axes[0, 1],
                map_data,
                "str_buildings_density",
                "Census Tract Level",
                "STR Buildings Density (per km²)",
                cmap="YlOrRd",
                bounds=common_bounds,
                stats_format="{:.2f}",
                logger=logger,
            )

        # --------- 2. Community Area Level Maps ---------
        if community_data is not None and community_boundaries is not None:
            community_map_data = community_boundaries.merge(
                community_data[
                    ["community_name", "str_buildings_count", "str_buildings_density"]
                ],
                on="community_name",
                how="left",
            )

            # Clip to city boundaries if available
            if city_boundaries is not None:
                if community_map_data.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(community_map_data.crs)
                community_map_data = gpd.clip(community_map_data, city_boundaries)
                logger.info("Clipped community data to Chicago city boundaries")

            # Count
            community_map_data.plot(
                column="str_buildings_count",
                ax=axes[1, 0],
                legend=True,
                cmap="YlOrRd",
                edgecolor="black",
                linewidth=0.5,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Buildings Count",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )
            axes[1, 0].set_title(
                f"Community Area Level Count (n={community_data['str_buildings_count'].notna().sum()})",
                fontsize=16,
            )
            axes[1, 0].axis("off")
            if common_bounds is not None:
                axes[1, 0].set_xlim(common_bounds[0], common_bounds[2])
                axes[1, 0].set_ylim(common_bounds[1], common_bounds[3])

            counts = community_data["str_buildings_count"].dropna()
            axes[1, 0].text(
                0.02,
                0.98,
                f"Min: {counts.min():.0f}\nMedian: {counts.median():.0f}\nMax: {counts.max():.0f}",
                transform=axes[1, 0].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

            # Density
            community_map_data.plot(
                column="str_buildings_density",
                ax=axes[1, 1],
                legend=True,
                cmap="YlOrRd",
                edgecolor="black",
                linewidth=0.5,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Buildings Density (per km²)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )
            axes[1, 1].set_title(
                f"Community Area Level Density (n={community_data['str_buildings_density'].notna().sum()})",
                fontsize=16,
            )
            axes[1, 1].axis("off")
            if common_bounds is not None:
                axes[1, 1].set_xlim(common_bounds[0], common_bounds[2])
                axes[1, 1].set_ylim(common_bounds[1], common_bounds[3])

            densities = community_data["str_buildings_density"].dropna()
            axes[1, 1].text(
                0.02,
                0.98,
                f"Min: {densities.min():.2f}\nMedian: {densities.median():.2f}\nMax: {densities.max():.2f}",
                transform=axes[1, 1].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

        # Save the plot
        output_path = Path(self.output_dir) / "str_buildings_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)
        plt.close()

        return {"str_buildings_map_plot": str(output_path)}
