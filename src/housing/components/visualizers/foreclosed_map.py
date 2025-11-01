"""Foreclosed property map visualizer.

This module creates choropleth maps showing foreclosed property
distributions at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Minimum land area in square meters to exclude water-only tracts
MIN_LAND_AREA_SQ_METERS = 10000


class ForeclosedMapVisualizer(Visualizer):
    """Create choropleth maps for foreclosed properties.

    Shows counts/density of foreclosed properties at census tract
    and community area levels.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the foreclosed map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "foreclosed_map_visualization",
            "Create choropleth maps for foreclosed properties",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create foreclosed property map visualizations."""
        logger.info("Creating foreclosed property map visualizations...")

        tract_data = context.get("foreclosed_tract_data")
        community_data = context.get("foreclosed_community_data")
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None and community_data is None:
            logger.warning("No foreclosed data available for mapping")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            "Chicago Foreclosed Properties by Geography",
            fontsize=20,
            fontweight="bold",
        )

        if city_boundaries is not None:
            common_bounds = city_boundaries.total_bounds

        # Common bounds for consistent zoom
        common_bounds = None
        if community_boundaries is not None:
            common_bounds = community_boundaries.total_bounds

        # 1. Census Tract Level Map
        if tract_data is not None and tract_boundaries is not None:
            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "foreclosed_count"]],
                on="tract_geoid",
                how="left",
            )

            # Filter small land tracts
            if "ALAND" in tract_map_data.columns:
                tract_map_data = tract_map_data[
                    tract_map_data["ALAND"] > MIN_LAND_AREA_SQ_METERS
                ].copy()
                logger.info("Filtered to %d tracts with land area", len(tract_map_data))

            # Choropleth using point_count
            tract_map_data.plot(
                column="foreclosed_count",
                ax=axes[0],
                legend=True,
                cmap="Reds",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Number of Foreclosed Properties",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[0].set_title(
                f"Census Tract Level (n={tract_data['foreclosed_count'].notna().sum()})",
                fontsize=16,
            )
            axes[0].axis("off")

            if common_bounds is not None:
                axes[0].set_xlim(common_bounds[0], common_bounds[2])
                axes[0].set_ylim(common_bounds[1], common_bounds[3])

            # Stats text
            counts = tract_data["foreclosed_count"].dropna()
            stats_text = (
                f"Min: {counts.min():.0f}\n"
                f"Median: {counts.median():.0f}\n"
                f"Max: {counts.max():.0f}"
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

        # 2. Community Area Level Map
        print(community_data.shape)
        print(community_boundaries.shape)
        if community_data is not None and community_boundaries is not None:
            community_map_data = community_boundaries.merge(
                community_data[["community_name", "foreclosed_count"]],
                on="community_name",
                how="left",
            )

            community_map_data.plot(
                column="foreclosed_count",
                ax=axes[1],
                legend=True,
                cmap="Reds",
                edgecolor="black",
                linewidth=0.5,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Number of Foreclosed Properties",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1].set_title(
                f"Community Area Level (n={community_data['foreclosed_count'].notna().sum()})",
                fontsize=16,
            )
            axes[1].axis("off")

            if common_bounds is not None:
                axes[1].set_xlim(common_bounds[0], common_bounds[2])
                axes[1].set_ylim(common_bounds[1], common_bounds[3])

            # Stats text
            counts = community_data["foreclosed_count"].dropna()
            stats_text = (
                f"Min: {counts.min():.0f}\n"
                f"Median: {counts.median():.0f}\n"
                f"Max: {counts.max():.0f}"
            )
            axes[1].text(
                0.02,
                0.98,
                stats_text,
                transform=axes[1].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

        plt.tight_layout()

        # Save the plot
        output_path = Path(self.output_dir) / "foreclosed_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"foreclosed_map_plot": str(output_path)}
