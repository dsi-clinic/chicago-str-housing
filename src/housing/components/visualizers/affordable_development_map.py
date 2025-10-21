"""Rental price map visualizer.

This module creates choropleth maps showing density of developments with affordable units and density of affordable units.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

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
        """Create rental price map visualizations."""
        logger.info("Creating rental price map visualizations...")

        tract_data = context.get("affordable_development_tract_data")
        tract_data = tract_data.loc[tract_data.point_density > 0]
        tract_boundaries = context.get("tract_boundaries")

        if tract_data is None:
            logger.warning("No tract level data available for mapping")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            "Chicago Affordable Development Density by Geography",
            fontsize=20,
            fontweight="bold",
        )

        # 1. Development Density Level Map
        if tract_data is not None and tract_boundaries is not None:
            # Merge tract data with boundaries for plotting
            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "point_density", "unit_density"]],
                on="tract_geoid",
                how="left",
            )

            # Filter out Lake Michigan and other water-only tracts
            # ALAND = land area in square meters; water tracts have ALAND = 0 or very small
            if "ALAND" in tract_map_data.columns:
                # Only keep tracts with significant land area
                tract_map_data = tract_map_data[
                    tract_map_data["ALAND"] > MIN_LAND_AREA_SQ_METERS
                ].copy()
                logger.info("Filtered to %d tracts with land area", len(tract_map_data))

            # Create choropleth
            tract_map_data.plot(
                column="point_density",
                ax=axes[0],
                legend=True,
                cmap="RdYlGn",  # Red (expensive) to Green (affordable)
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

            axes[0].set_title(
                f"Building Density (n={tract_data['point_density'].notna().sum()})",
                fontsize=16,
            )
            axes[0].axis("off")

            # Add statistics text
            point_density = tract_data["point_density"].dropna()
            stats_text = (
                f"Min: ${point_density.min():.0f}\n"
                f"Median: ${point_density.median():.0f}\n"
                f"Max: ${point_density.max():.0f}"
            )
            axes[0].text(
                0.02,
                0.98,
                stats_text,
                transform=axes[0].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

            # 2. Unit Density Level Map

            # Create choropleth
            tract_map_data.plot(
                column="unit_density",
                ax=axes[1],
                legend=True,
                cmap="RdYlGn",  # Red (expensive) to Green (affordable)
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

            axes[1].set_title(
                f"Unit Density (n={tract_data['unit_density'].notna().sum()})",
                fontsize=16,
            )
            axes[1].axis("off")

            # Add statistics text
            unit_density = tract_data["unit_density"].dropna()
            stats_text = (
                f"Min: ${unit_density.min():.0f}\n"
                f"Median: ${unit_density.median():.0f}\n"
                f"Max: ${unit_density.max():.0f}"
            )
            axes[1].text(
                0.02,
                0.98,
                stats_text,
                transform=axes[0].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

        plt.tight_layout()

        # Save the plot
        output_path = Path(self.output_dir) / "affordable_development_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"affordable_development_map_plot": str(output_path)}
