"""RACS Census Tract map visualizer.

This module creates choropleth maps showing rental price distributions
at tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
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
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create tract acs map visualizations."""
        logger.info("Creating tract acs map visualizations...")

        tract_data = context["acs_tract_data"]
        community_data = context["acs_community_data"]
        tract_boundaries = context.get("tract_boundaries")
        community_boundaries = context.get("community_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None:
            logger.warning("No rental data available for mapping")
            return {}

        # Excluding the Lake Michigan GEOID
        tract_data = tract_data[tract_data["GEOID"] != "17031990000"]
        # zexluding Outlier
        tract_data = tract_data[tract_data["GEOID"] != "17031030702"]

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(15, 10))
        fig.suptitle(
            "Chicago Information by Geography",
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
                tract_data[["tract_geoid", "population_density"]],
                on="tract_geoid",
                how="left",
            )

            # Filter small land tracts
            if "ALAND" in tract_map_data.columns:
                tract_map_data = tract_map_data[
                    tract_map_data["ALAND"] > MIN_LAND_AREA_SQ_METERS
                ].copy()
                logger.info("Filtered to %d tracts with land area", len(tract_map_data))
        tract_map_data = gpd.clip(tract_map_data, city_boundaries)

        # 1. Create choropleth for population density
        tract_map_data.plot(
            column="population_density",
            ax=axes[0],
            legend=True,
            cmap="YlOrRd",
            edgecolor="black",
            linewidth=0.1,
            missing_kwds={"color": "lightgrey", "label": "No Data"},
            legend_kwds={
                "label": "Population Density (per km2)",
                "orientation": "horizontal",
                "shrink": 0.8,
                "pad": 0.05,
            },
        )
        axes[0].set_title(
            f"Population Density Census Tract Level (n={tract_data['population_density'].notna().sum()})",
            fontsize=16,
        )
        axes[0].axis("off")

        if common_bounds is not None:
            axes[0].set_xlim(common_bounds[0], common_bounds[2])
            axes[0].set_ylim(common_bounds[1], common_bounds[3])

        # Add statistics text
        tract_population = tract_data["population_density"].dropna()
        stats_text = (
            f"Min: {tract_population.min():.0f}\n"
            f"Median: {tract_population.median():.0f}\n"
            f"Max: {tract_population.max():.0f}"
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

        # 2. Create choropleth for population density community
        community_data.plot(
            column="population_density",
            ax=axes[1],
            legend=True,
            cmap="YlOrRd",
            edgecolor="black",
            linewidth=0.1,
            missing_kwds={"color": "lightgrey", "label": "No Data"},
            legend_kwds={
                "label": "Population Density (per km2)",
                "orientation": "horizontal",
                "shrink": 0.8,
                "pad": 0.05,
            },
        )
        axes[1].set_title(
            f"Population Density (n={tract_data['population_density'].notna().sum()})",
            fontsize=16,
        )
        axes[1].axis("off")

        # Add statistics text
        tract_population = tract_data["population_density"].dropna()
        stats_text = (
            f"Min: {tract_population.min():.0f}\n"
            f"Median: {tract_population.median():.0f}\n"
            f"Max: {tract_population.max():.0f}"
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
        output_path = Path(self.output_dir) / "acs_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"rental_map_plot": str(output_path)}
