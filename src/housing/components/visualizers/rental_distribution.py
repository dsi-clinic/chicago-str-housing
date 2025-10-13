"""Rental price distribution visualizer.

This module creates visualizations showing rental price distributions
at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

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
        fig.suptitle(
            "Chicago Rental Price Distribution: Tract vs Community Area",
            fontsize=18,
            fontweight="bold",
        )

        # 1. Tract-level rental price distribution
        if tract_data is not None:
            tract_prices = tract_data["avg_rental_price"].dropna()
            axes[0, 0].hist(
                tract_prices,
                bins=30,
                alpha=0.7,
                color="steelblue",
                edgecolor="black",
            )
            axes[0, 0].axvline(
                tract_prices.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: ${tract_prices.median():.0f}",
            )
            axes[0, 0].set_xlabel("Average Rental Price ($)", fontsize=12)
            axes[0, 0].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 0].set_title(
                f"Census Tract Level (n={len(tract_prices)})", fontsize=14
            )
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # 2. Community-level rental price distribution
        if community_data is not None:
            community_prices = community_data["avg_rental_price"].dropna()
            axes[0, 1].hist(
                community_prices,
                bins=20,
                alpha=0.7,
                color="forestgreen",
                edgecolor="black",
            )
            axes[0, 1].axvline(
                community_prices.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: ${community_prices.median():.0f}",
            )
            axes[0, 1].set_xlabel("Average Rental Price ($)", fontsize=12)
            axes[0, 1].set_ylabel("Number of Community Areas", fontsize=12)
            axes[0, 1].set_title(
                f"Community Area Level (n={len(community_prices)})", fontsize=14
            )
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()

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
        axes[1, 1].axis("off")
        stats_lines = ["Rental Price Statistics\n" + "=" * 40 + "\n"]

        if tract_data is not None:
            tract_prices = tract_data["avg_rental_price"].dropna()
            stats_lines.append("CENSUS TRACT LEVEL:")
            stats_lines.append(f"  Count: {len(tract_prices)}")
            stats_lines.append(f"  Mean: ${tract_prices.mean():.2f}")
            stats_lines.append(f"  Median: ${tract_prices.median():.2f}")
            stats_lines.append(f"  Std Dev: ${tract_prices.std():.2f}")
            stats_lines.append(f"  Min: ${tract_prices.min():.2f}")
            stats_lines.append(f"  Max: ${tract_prices.max():.2f}")
            stats_lines.append(f"  Q1: ${tract_prices.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: ${tract_prices.quantile(0.75):.2f}")
            stats_lines.append("")

        if community_data is not None:
            community_prices = community_data["avg_rental_price"].dropna()
            stats_lines.append("COMMUNITY AREA LEVEL:")
            stats_lines.append(f"  Count: {len(community_prices)}")
            stats_lines.append(f"  Mean: ${community_prices.mean():.2f}")
            stats_lines.append(f"  Median: ${community_prices.median():.2f}")
            stats_lines.append(f"  Std Dev: ${community_prices.std():.2f}")
            stats_lines.append(f"  Min: ${community_prices.min():.2f}")
            stats_lines.append(f"  Max: ${community_prices.max():.2f}")
            stats_lines.append(f"  Q1: ${community_prices.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: ${community_prices.quantile(0.75):.2f}")

        stats_text = "\n".join(stats_lines)

        axes[1, 1].text(
            0.05,
            0.95,
            stats_text,
            transform=axes[1, 1].transAxes,
            fontsize=11,
            verticalalignment="top",
            fontfamily="monospace",
            bbox={"boxstyle": "round,pad=0.8", "facecolor": "lightgray", "alpha": 0.8},
        )

        plt.tight_layout()

        # Save the plot
        output_path = Path(self.output_dir) / "rental_distribution_analysis.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.close()

        return {"rental_distribution_plot": str(output_path)}
