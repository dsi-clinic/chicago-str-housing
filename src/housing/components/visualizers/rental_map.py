"""Rental price map visualizer.

This module creates choropleth maps showing rental price distributions
at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


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
        city_boundaries = context.get("city_boundaries")

        if tract_data is None and community_data is None:
            logger.warning("No rental data available for mapping")
            return {}

        # Create figure with 2 subplots for tract and community level maps
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            "Chicago Average Rental Prices", fontsize=20, fontweight="bold", y=0.98
        )

        # Get common bounds for consistent zoom
        if city_boundaries is not None:
            common_bounds = city_boundaries.total_bounds
        else:
            common_bounds = None

        # 1. Census Tract Level Map
        if tract_data is not None and tract_boundaries is not None:
            from housing.components.utils import create_choropleth_map, prepare_map_data

            map_data = prepare_map_data(
                tract_data,
                tract_boundaries,
                ["avg_rental_price"],
                city_boundaries,
                logger=logger,
            )
            create_choropleth_map(
                axes[0],
                map_data,
                "avg_rental_price",
                "Census Tract Level",
                "Average Rental Price ($)",
                cmap="RdYlGn_r",
                bounds=common_bounds,
                stats_format="${:.0f}",
                logger=logger,
            )

        # 2. Community Area Level Map
        if community_data is not None and community_boundaries is not None:
            # Merge community data with boundaries for plotting
            community_map_data = community_boundaries.merge(
                community_data[["community_name", "avg_rental_price"]],
                on="community_name",
                how="left",
            )

            # Clip to city boundaries if available
            if city_boundaries is not None:
                import geopandas as gpd

                # Ensure same CRS
                if community_map_data.crs != city_boundaries.crs:
                    city_boundaries = city_boundaries.to_crs(community_map_data.crs)
                # Clip community areas to city boundary
                community_map_data = gpd.clip(community_map_data, city_boundaries)
                logger.info("Clipped community data to Chicago city boundaries")

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

        # Save the plot
        output_path = Path(self.output_dir) / "rental_price_maps.png"
        setup_figure_and_save(
            fig,
            output_path,
            title="Chicago Average Rental Prices by Census Tract and Community Area",
            logger=logger,
        )

        return {"rental_map_plot": str(output_path)}
