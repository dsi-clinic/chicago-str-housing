"""STR prohibition map visualizer.

This module creates choropleth maps showing STR prohibition distributions
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


class STRMapVisualizer(Visualizer):
    """Create choropleth maps for STR prohibitions.

    Shows STR prohibition data as geographic maps at census tract level.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR map visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_map_visualization",
            "Create choropleth maps for STR prohibitions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR prohibition map visualizations."""
        logger.info("Creating STR prohibition map visualizations...")

        tract_data = context.get("str_tract_analysis")
        tract_boundaries = context.get("tract_boundaries")
        city_boundaries = context.get("city_boundaries")

        if tract_data is None:
            logger.warning("No STR tract data available for mapping")
            return {}

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping map visualization")
            return {}

        # Create figure with subplots (two panels: units density, buildings density)
        fig, axes = plt.subplots(1, 2, figsize=(22, 10))
        fig.suptitle(
            "Chicago STR Prohibition Analysis by Census Tract",
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

        # 1. STR Prohibition Density Choropleth
        if "str_prohibition_density" in tract_data.columns:
            # Merge tract data with boundaries for plotting
            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "str_prohibition_density"]],
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
                column="str_prohibition_density",
                ax=axes[0],
                legend=True,
                cmap="YlOrRd",  # Yellow to red gradient
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Units Density (per km²)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[0].set_title(
                f"STR Units Density (n={tract_data['str_prohibition_density'].notna().sum()})",
                fontsize=16,
            )
            axes[0].axis("off")

            # Set common bounds
            axes[0].set_xlim(common_bounds[0], common_bounds[2])
            axes[0].set_ylim(common_bounds[1], common_bounds[3])

            # Add statistics text
            str_density = tract_data["str_prohibition_density"].dropna()
            stats_text = (
                f"Min: {str_density.min():.1f}\n"
                f"Median: {str_density.median():.1f}\n"
                f"Max: {str_density.max():.1f}"
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

        # 2. Buildings per km² Choropleth (building density)
        if (
            "str_prohibition_count" in tract_data.columns
            and "area_km2" in tract_data.columns
        ):
            tract_data = tract_data.copy()
            tract_data["building_density"] = (
                tract_data["str_prohibition_count"] / tract_data["area_km2"]
            )

            tract_map_data = tract_boundaries.merge(
                tract_data[["tract_geoid", "building_density"]],
                on="tract_geoid",
                how="left",
            )

            if "ALAND" in tract_map_data.columns:
                tract_map_data = tract_map_data[
                    tract_map_data["ALAND"] > MIN_LAND_AREA_SQ_METERS
                ].copy()

            if city_boundaries is not None:
                import geopandas as gpd

                if tract_map_data.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(tract_map_data.crs)
                tract_map_data = gpd.clip(tract_map_data, city_boundaries)

            tract_map_data.plot(
                column="building_density",
                ax=axes[1],
                legend=True,
                cmap="Oranges",
                edgecolor="black",
                linewidth=0.1,
                missing_kwds={"color": "lightgrey", "label": "No Data"},
                legend_kwds={
                    "label": "STR Buildings Density (per km²)",
                    "orientation": "horizontal",
                    "shrink": 0.8,
                    "pad": 0.05,
                },
            )

            axes[1].set_title(
                f"STR Buildings Density (n={tract_data['building_density'].notna().sum()})",
                fontsize=16,
            )
            axes[1].axis("off")

            axes[1].set_xlim(common_bounds[0], common_bounds[2])
            axes[1].set_ylim(common_bounds[1], common_bounds[3])

        plt.tight_layout()
        plt.subplots_adjust(top=0.85)  # Increase space for title

        # Save the plot
        output_path = Path(self.output_dir) / "str_density_maps.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved map visualization to: %s", output_path)

        plt.close()

        return {"str_map_plot": str(output_path)}
