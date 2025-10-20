"""Rental price distribution visualizer.

This module creates visualizations showing rental price distributions
at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    add_statistical_summary_to_plot,
    create_histogram_with_median,
    setup_figure_and_save,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class RentalDistributionVisualizer(Visualizer):
    """Create visualizations for rental price distributions.

    Shows rental prices aggregated at both census tract and community area
    levels to demonstrate the hierarchical spatial aggregation.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the rental distribution visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "rental_distribution_visualization",
            "Create visualizations for rental price distributions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create rental distribution visualizations."""
        logger.info("Creating rental distribution visualizations...")

        tract_data = context.get("tract_rental_data")
        community_data = context.get("community_rental_data")

        if tract_data is None and community_data is None:
            logger.warning("No rental data available for visualization")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Tract-level rental price distribution
        if tract_data is not None:
            create_histogram_with_median(
                axes[0, 0],
                tract_data["avg_rental_price"],
                "Census Tract Level",
                "Average Rental Price ($)",
                "Number of Census Tracts",
                color="steelblue",
                median_format="${:.0f}",
            )

        # 2. Community-level rental price distribution
        if community_data is not None:
            create_histogram_with_median(
                axes[0, 1],
                community_data["avg_rental_price"],
                "Community Area Level",
                "Average Rental Price ($)",
                "Number of Community Areas",
                color="forestgreen",
                bins=20,
                median_format="${:.0f}",
            )

        # 3. Box plots for comparison
        if tract_data is not None and community_data is not None:
            tract_prices = tract_data["avg_rental_price"].dropna()
            community_prices = community_data["avg_rental_price"].dropna()

            box_data = [tract_prices, community_prices]
            bp = axes[1, 0].boxplot(
                box_data,
                labels=["Census Tract", "Community Area"],
                patch_artist=True,
                showmeans=True,
                meanline=True,
            )
            # Color the boxes
            bp["boxes"][0].set_facecolor("steelblue")
            bp["boxes"][1].set_facecolor("forestgreen")

            axes[1, 0].set_ylabel("Average Rental Price ($)", fontsize=12)
            axes[1, 0].set_title("Rental Price Distribution Comparison", fontsize=14)
            axes[1, 0].grid(True, alpha=0.3, axis="y")

        # 4. Statistical summary
        data_sections = []

        if tract_data is not None:
            tract_prices = tract_data["avg_rental_price"].dropna()
            data_sections.append(
                {
                    "section_title": "CENSUS TRACT LEVEL",
                    "stats": [
                        ("Count", len(tract_prices)),
                        ("Mean", f"${tract_prices.mean():.2f}"),
                        ("Median", f"${tract_prices.median():.2f}"),
                        ("Std Dev", f"${tract_prices.std():.2f}"),
                        ("Min", f"${tract_prices.min():.2f}"),
                        ("Max", f"${tract_prices.max():.2f}"),
                        ("Q1", f"${tract_prices.quantile(0.25):.2f}"),
                        ("Q3", f"${tract_prices.quantile(0.75):.2f}"),
                    ],
                }
            )

        if community_data is not None:
            community_prices = community_data["avg_rental_price"].dropna()
            data_sections.append(
                {
                    "section_title": "COMMUNITY AREA LEVEL",
                    "stats": [
                        ("Count", len(community_prices)),
                        ("Mean", f"${community_prices.mean():.2f}"),
                        ("Median", f"${community_prices.median():.2f}"),
                        ("Std Dev", f"${community_prices.std():.2f}"),
                        ("Min", f"${community_prices.min():.2f}"),
                        ("Max", f"${community_prices.max():.2f}"),
                        ("Q1", f"${community_prices.quantile(0.25):.2f}"),
                        ("Q3", f"${community_prices.quantile(0.75):.2f}"),
                    ],
                }
            )

        add_statistical_summary_to_plot(
            axes[1, 1],
            "Rental Price Statistics",
            data_sections,
            bgcolor="lightgray",
        )

        # Save the plot
        output_path = Path(self.output_dir) / "rental_distribution_analysis.png"
        setup_figure_and_save(
            fig,
            output_path,
            "Chicago Rental Price Distribution: Tract vs Community Area",
            logger=logger,
        )

        return {"rental_distribution_plot": str(output_path)}
