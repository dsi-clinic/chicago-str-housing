"""Airbnb price map visualizer.

This module creates choropleth maps showing Airbnb price distributions
at census tract level.
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


class AirbnbMapVisualizer(Visualizer):
    """Create choropleth maps for Airbnb prices.

    Shows Airbnb prices as geographic maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the Airbnb map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "airbnb_map_visualization",
            "Create choropleth maps for Airbnb prices",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create Airbnb price map visualizations."""
        logger.info("Creating Airbnb price map visualizations...")

        tract_data = context.get("airbnb_tract_data")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None:
            logger.warning("No Airbnb tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            "Chicago Airbnb Analysis by Census Tract",
            fontsize=20,
            fontweight="bold",
            y=0.98,  # Move title higher
        )

        # Get bounds from city boundaries for proper zoom on Chicago
        if city_boundaries is not None:
            # Use city boundaries for zoom
            common_bounds = city_boundaries.total_bounds  # [minx, miny, maxx, maxy]
        else:
            # Fallback to tract boundaries
            common_bounds = tract_boundaries.total_bounds

        # 1. Airbnb Price Choropleth
        if "price_numeric_mean" in tract_data.columns:
            # Merge tract data with boundaries for plotting
            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "price_numeric_mean"]],
                on="tract_geoid",
                how="left",
            )

            # Filter out Lake Michigan and other water-only tracts
            if "ALAND" in tract_map_data.columns:
                tract_map_data = tract_map_data[
                    tract_map_data["ALAND"] > MIN_LAND_AREA_SQ_METERS
                ].copy()
                logger.info("Filtered to %d tracts with land area", len(tract_map_data))

            # Clip to city boundaries if available
            if city_boundaries is not None:
                import geopandas as gpd

                # Ensure same CRS
                if tract_map_data.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(tract_map_data.crs)
                # Clip tracts to city boundary
                tract_map_data = gpd.clip(tract_map_data, city_boundaries)
                logger.info("Clipped tract data to Chicago city boundaries")

            # Create choropleth
            tract_map_data.plot(
                column="price_numeric_mean",
                ax=axes[0],
                legend=True,
                cmap="viridis",  # Purple to yellow gradient
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Average Airbnb Price ($)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[0].set_title(
                f"Airbnb Price Distribution (n={tract_data['price_numeric_mean'].notna().sum()})",
                fontsize=16,
            )
            axes[0].axis("off")

            # Set common bounds
            axes[0].set_xlim(common_bounds[0], common_bounds[2])
            axes[0].set_ylim(common_bounds[1], common_bounds[3])

            # Add statistics text
            airbnb_prices = tract_data["price_numeric_mean"].dropna()
            stats_text = (
                f"Min: ${airbnb_prices.min():.0f}\n"
                f"Median: ${airbnb_prices.median():.0f}\n"
                f"Max: ${airbnb_prices.max():.0f}"
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

        # 2. Airbnb Density Choropleth
        if "point_density" in tract_data.columns:
            # Merge tract data with boundaries for plotting
            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "point_density"]],
                on="tract_geoid",
                how="left",
            )

            # Filter out Lake Michigan and other water-only tracts
            if "ALAND" in tract_map_data.columns:
                tract_map_data = tract_map_data[
                    tract_map_data["ALAND"] > MIN_LAND_AREA_SQ_METERS
                ].copy()

            # Clip to city boundaries if available
            if city_boundaries is not None:
                import geopandas as gpd

                # Ensure same CRS
                if tract_map_data.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(tract_map_data.crs)
                # Clip tracts to city boundary
                tract_map_data = gpd.clip(tract_map_data, city_boundaries)

            # Create choropleth
            tract_map_data.plot(
                column="point_density",
                ax=axes[1],
                legend=True,
                cmap="Blues",  # Light to dark blue gradient
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "Airbnb Density (listings per km²)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1].set_title(
                f"Airbnb Density Distribution (n={tract_data['point_density'].notna().sum()})",
                fontsize=16,
            )
            axes[1].axis("off")

            # Set common bounds
            axes[1].set_xlim(common_bounds[0], common_bounds[2])
            axes[1].set_ylim(common_bounds[1], common_bounds[3])

            # Add statistics text
            airbnb_density = tract_data["point_density"].dropna()
            stats_text = (
                f"Min: {airbnb_density.min():.1f}\n"
                f"Median: {airbnb_density.median():.1f}\n"
                f"Max: {airbnb_density.max():.1f}"
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
        plt.subplots_adjust(top=0.85)  # Increase space for title

        # Save the plot
        output_path = Path(self.output_dir) / "airbnb_analysis_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"airbnb_map_plot": str(output_path)}
