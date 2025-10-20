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


class ACSMapVisualizer(Visualizer):
    """Create choropleth maps for the tract acs data"""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the rental map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "acs_map_visualization",
            "Create choropleth maps for the tract ACS",
        )
        self.output_dir = output_dir or "/project/data/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create tract acs map visualizations."""
        logger.info("Creating tract acs map visualizations...")

        tract_data = context["acs_tract_data"]

        if tract_data is None:
            logger.warning("No rental data available for mapping")
            return {}

        # Excluding the Lake Michigan GEOID
        tract_data = tract_data[tract_data["GEOID"] != "17031990000"]
        # zexluding Outlier
        tract_data = tract_data[tract_data["GEOID"] != "17031030702"]

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            "Chicago Average Population Density by Geography",
            fontsize=20,
            fontweight="bold",
        )

        # 1. Create choropleth for population density
        tract_data.plot(
            column="population_density",
            ax=axes[0],
            legend=True,
            cmap="RdYlGn_r",  # Red (dense) to Green (sparse)
            edgecolor="black",
            linewidth=0.1,
            missing_kwds={"color": "lightgrey", "label": "No Data"},
            legend_kwds={
                "label": "Population Density",
                "orientation": "vertical",
                "shrink": 0.8,
                "pad": 0.05,
            },
        )

        axes[0].set_title(
            f"Census Tract Level (n={tract_data['population_density'].notna().sum()})",
            fontsize=16,
        )
        axes[0].axis("off")

        # Add statistics text
        tract_population = tract_data["population_density"].dropna()
        stats_text = (
            "Population per km^2 \n"
            f"Min: {tract_population.min():.0f}\n"
            f"Median: {tract_population.median():.0f}\n"
            f"Max: {tract_population.max():.0f}"
        )
        axes[0].text(
            0.18,
            0.6,
            stats_text,
            transform=axes[0].transAxes,
            fontsize=12,
            horizontalalignment="left",
            verticalalignment="bottom",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "white", "alpha": 0.8},
        )

        # 2. Create histogram of population density
        axes[1].hist(
            tract_population,
            bins=30,
            alpha=0.7,
            color="steelblue",
            edgecolor="black",
        )
        axes[1].axvline(
            tract_population.median(),
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Median: ${tract_population.median():.0f}",
        )
        axes[1].set_xlabel("Populetion per km^2", fontsize=12)
        axes[1].set_ylabel("Number of Census Tracts", fontsize=12)
        axes[1].set_title(
            f"Census Tract Level (n={len(tract_population)})", fontsize=14
        )
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()

        plt.tight_layout()

        # Save the plot
        output_path = Path(self.output_dir) / "acs_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"rental_map_plot": str(output_path)}
