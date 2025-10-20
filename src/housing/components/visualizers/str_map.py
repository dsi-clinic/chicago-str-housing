"""STR map visualizer.

This module creates choropleth maps showing STR count distributions
at both tract and community area levels.
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


class STRMapVisualizer(Visualizer):
    """Create choropleth maps for STR Buildings List.

    Shows STR count as geographic maps at both census tract and
    community area levels.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_map_visualization",
            "Create choropleth maps for STR data",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR map visualizations."""
        logger.info("Creating STR map visualizations...")

        tract_data = context.get("str_tract_data")
        community_data = context.get("community_str_data")
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")

        if tract_data is None and community_data is None:
            logger.warning("No STR data available for mapping")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(20, 12))
        fig.suptitle(
            "Chicago Short-Term Rentals by Geography",
            fontsize=20,
            fontweight="bold",
        )

        # Get common bounds from community boundaries for consistent zoom
        common_bounds = None
        if community_boundaries is not None:
            common_bounds = community_boundaries.total_bounds

        # 1. Census Tract Level Map
        if tract_data is not None and tract_boundaries is not None:
            # Merge tract data with boundaries for plotting
            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "point_count", "point_density"]],
                on="tract_geoid",
                how="left",
            )

            # Filter out water-only tracts
            if "ALAND" in tract_map_data.columns:
                tract_map_data = tract_map_data[
                    tract_map_data["ALAND"] > MIN_LAND_AREA_SQ_METERS
                ].copy()
                logger.info("Filtered to %d tracts with land area", len(tract_map_data))

            # Map 1: count of STR listings
            tract_map_data.plot(
                column="point_count",
                ax=axes[0, 0],
                legend=True,
                cmap="RdYlGn_r",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Listings (Count)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[0, 0].set_title(
                f"STR Count per Census Tract (n={tract_data['point_count'].notna().sum()})",
                fontsize=16,
            )
            axes[0, 0].axis("off")

            if common_bounds is not None:
                axes[0, 0].set_xlim(common_bounds[0], common_bounds[2])
                axes[0, 0].set_ylim(common_bounds[1], common_bounds[3])

            counts = tract_data["point_count"].dropna()
            stats_text = (
                f"Min: {counts.min():.0f}\n"
                f"Median: {counts.median():.0f}\n"
                f"Max: {counts.max():.0f}"
            )
            axes[0, 0].text(
                0.02,
                0.98,
                stats_text,
                transform=axes[0, 0].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

            # Map 2: density of STR listings
            tract_map_data.plot(
                column="point_density",
                ax=axes[0, 1],
                legend=True,
                cmap="RdYlGn_r",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Density (listings/km²)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[0, 1].set_title(
                f"STR Density per Census Tract (n={tract_data['point_density'].notna().sum()})",
                fontsize=16,
            )
            axes[0, 1].axis("off")

            if common_bounds is not None:
                axes[0, 1].set_xlim(common_bounds[0], common_bounds[2])
                axes[0, 1].set_ylim(common_bounds[1], common_bounds[3])

            densities = tract_data["point_density"].dropna()
            stats_text = (
                f"Min: {densities.min():.2f}\n"
                f"Median: {densities.median():.2f}\n"
                f"Max: {densities.max():.2f}"
            )
            axes[0, 1].text(
                0.02,
                0.98,
                stats_text,
                transform=axes[0, 1].transAxes,
                fontsize=12,
                verticalalignment="top",
                bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
            )

        # 2. Community Area Level Map
        if community_data is not None and community_boundaries is not None:
            # Merge community data with boundaries for plotting
            community_map_data = community_boundaries.merge(
                community_data[["community", "point_count", "point_density"]],
                on="community",
                how="left",
            )

            # Map 3: count
            community_map_data.plot(
                column="point_count",
                ax=axes[1, 0],
                legend=True,
                cmap="RdYlGn_r",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Listings (Count)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1, 0].set_title(
                f"STR Count by Community Area (n={community_data['point_count'].notna().sum()})",
                fontsize=16,
            )
            axes[1, 0].axis("off")

            if common_bounds is not None:
                axes[1, 0].set_xlim(common_bounds[0], common_bounds[2])
                axes[1, 0].set_ylim(common_bounds[1], common_bounds[3])

            counts = community_data["point_count"].dropna()
            stats_text = (
                f"Min: {counts.min():.0f}\n"
                f"Median: {counts.median():.0f}\n"
                f"Max: {counts.max():.0f}"
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

            # Map 4: density
            community_map_data.plot(
                column="point_density",
                ax=axes[1, 1],
                legend=True,
                cmap="RdYlGn_r",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Density (listings/km²)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1, 1].set_title(
                f"STR Density by Community Area (n={community_data['point_density'].notna().sum()})",
                fontsize=16,
            )
            axes[1, 1].axis("off")

            if common_bounds is not None:
                axes[1, 1].set_xlim(common_bounds[0], common_bounds[2])
                axes[1, 1].set_ylim(common_bounds[1], common_bounds[3])

            density = community_data["point_density"].dropna()
            stats_text = (
                f"Min: {density.min():.2f}\n"
                f"Median: {density.median():.2f}\n"
                f"Max: {density.max():.2f}"
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

        # Save the plot
        output_path = Path(self.output_dir) / "str_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)
        plt.close()

        return {"str_map_plot": str(output_path)}
