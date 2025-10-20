"""Rental price map visualizer.

This module creates choropleth maps showing rental price distributions
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

class RentalMapVisualizer(Visualizer):
    """Create choropleth maps for rental prices.

    Shows rental prices as geographic maps at both census tract and
    community area levels.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the rental map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "rental_map_visualization",
            "Create choropleth maps for rental prices",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create rental price map visualizations."""
        logger.info("Creating rental price map visualizations...")

        tract_data = context.get("tract_rental_data")
        community_data = context.get("community_rental_data")
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")

        if tract_data is None and community_data is None:
            logger.warning("No rental data available for mapping")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            "Chicago Average Rental Prices by Geography",
            fontsize=20,
            fontweight="bold",
        )

        # Get common bounds from community boundaries for consistent zoom
        common_bounds = None
        if community_boundaries is not None:
            common_bounds = (
                community_boundaries.total_bounds
            )  # [minx, miny, maxx, maxy]

        # 1. Census Tract Level Map
        if tract_data is not None and tract_boundaries is not None:
            # Merge tract data with boundaries for plotting
            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "avg_rental_price"]],
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
                column="avg_rental_price",
                ax=axes[0],
                legend=True,
                cmap="RdYlGn_r",  # Red (expensive) to Green (affordable)
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Average Rental Price ($)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[0].set_title(
                f"Census Tract Level (n={tract_data['avg_rental_price'].notna().sum()})",
                fontsize=16,
            )
            axes[0].axis("off")

            # Set common bounds if available
            if common_bounds is not None:
                axes[0].set_xlim(common_bounds[0], common_bounds[2])
                axes[0].set_ylim(common_bounds[1], common_bounds[3])

            # Add statistics text
            tract_prices = tract_data["avg_rental_price"].dropna()
            stats_text = (
                f"Min: ${tract_prices.min():.0f}\n"
                f"Median: ${tract_prices.median():.0f}\n"
                f"Max: ${tract_prices.max():.0f}"
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
        if community_data is not None and community_boundaries is not None:
            # Merge community data with boundaries for plotting
            community_map_data = community_boundaries.merge(
                community_data[["community_name", "avg_rental_price"]],
                on="community_name",
                how="left",
            )

            # Create choropleth
            community_map_data.plot(
                column="avg_rental_price",
                ax=axes[1],
                legend=True,
                cmap="RdYlGn_r",  # Red (expensive) to Green (affordable)
                edgecolor="black",
                linewidth=0.5,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Average Rental Price ($)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1].set_title(
                f"Community Area Level (n={community_data['avg_rental_price'].notna().sum()})",
                fontsize=16,
            )
            axes[1].axis("off")

            # Set common bounds if available
            if common_bounds is not None:
                axes[1].set_xlim(common_bounds[0], common_bounds[2])
                axes[1].set_ylim(common_bounds[1], common_bounds[3])

            # Add statistics text
            community_prices = community_data["avg_rental_price"].dropna()
            stats_text = (
                f"Min: ${community_prices.min():.0f}\n"
                f"Median: ${community_prices.median():.0f}\n"
                f"Max: ${community_prices.max():.0f}"
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
        output_path = Path(self.output_dir) / "rental_price_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"rental_map_plot": str(output_path)}
