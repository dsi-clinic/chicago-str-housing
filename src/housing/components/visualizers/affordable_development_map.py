"""Rental price map visualizer.

This module creates choropleth maps showing density of developments with affordable units and density of affordable units.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    create_choropleth_map,
    prepare_map_data,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Minimum land area in square meters to exclude water-only tracts
# 10,000 sq meters = ~2.5 acres
MIN_LAND_AREA_SQ_METERS = 10000


class AffordableMapVisualizer(Visualizer):
    """Create choropleth maps for affordable developments.

    Shows affordable development density at the building and unit level in cloropleth maps.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the affordable development map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "affordable_development_map_visualization",
            "Create choropleth maps for affordable development density",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create affordable development density map visualizations."""
        logger.info("Creating affordable development density map visualizations...")

        tract_data = context.get("affordable_developments_tract_data")
        community_data = context.get("affordable_developments_community_data")
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None:
            logger.warning("No tract level data available for mapping")
            return {}

        if community_data is None:
            logger.warning("No community level data available for mapping")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 20))
        fig.suptitle(
            "Chicago Affordable Development Density by Geography",
            fontsize=20,
            fontweight="bold",
        )

        # ONE: Tract-Level Maps
        map_data = prepare_map_data(
            tract_data,
            tract_boundaries,
            ["affordable_development_density", "affordable_development_unit_density"],
            city_boundaries,
            logger=logger,
        )

        # Create the buildings choropleth map
        create_choropleth_map(
            axes[0, 0],
            map_data,
            "affordable_development_density",
            "Affordable Development Building Density",
            "Affordable Development Building Density per km2",
            cmap="YlOrRd",
            stats_format="{:.0f}",
            logger=logger,
        )

        # create the units choropleth map
        create_choropleth_map(
            axes[0, 1],
            map_data,
            "affordable_development_unit_density",
            "Affordable Development Unit Density",
            "Affordable Development Unit Density per km2",
            cmap="YlOrRd",
            stats_format="{:.0f}",
            logger=logger,
        )

        # TWO: Community area-level maps

        if community_data is not None and community_boundaries is not None:
            # 1. Building Density
            # Merge community data with boundaries for plotting
            community_map_data = community_boundaries.merge(
                community_data[
                    [
                        "community_area",
                        "affordable_development_density",
                        "affordable_development_unit_density",
                    ]
                ],
                on="community_area",
                how="left",
            )

            # Create choropleth
            community_map_data.plot(
                column="affordable_development_density",
                ax=axes[1, 0],
                legend=True,
                cmap="YlOrRd",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Affordable Development Building Density per km2",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1, 0].set_title(
                f"Affordable Development Building Density (n={community_data["affordable_development_density"].notna().sum()})",
                fontsize=16,
            )
            axes[1, 0].axis("off")

            # Add statistics text
            point_density = community_data["affordable_development_density"].dropna()
            stats_text = (
                f"Min: {point_density.min():.0f}\n"
                f"Median: {point_density.median():.0f}\n"
                f"Max: {point_density.max():.0f}"
            )
            axes[1, 0].text(
                0.02,
                0.98,
                stats_text,
                transform=axes[1, 0].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

            # 2. Unit Density Level Map

            # Create choropleth
            community_map_data.plot(
                column="affordable_development_unit_density",
                ax=axes[1, 1],
                legend=True,
                cmap="YlOrRd",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Affordable Development Unit Density per km2",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1, 1].set_title(
                f"Affordable Development Unit Density (n={community_data["affordable_development_unit_density"].notna().sum()})",
                fontsize=16,
            )
            axes[1, 1].axis("off")

            # Add statistics text
            unit_density = community_data[
                "affordable_development_unit_density"
            ].dropna()
            stats_text = (
                f"Min: {unit_density.min():.0f}\n"
                f"Median: {unit_density.median():.0f}\n"
                f"Max: {unit_density.max():.0f}"
            )
            axes[1, 1].text(
                0.02,
                0.98,
                stats_text,
                transform=axes[1, 1].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

        fig.tight_layout(rect=[0, 0, 1, 0.98])

        # Save the plot
        output_path = Path(self.output_dir) / "affordable_development_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"affordable_development_map_plot": str(output_path)}
