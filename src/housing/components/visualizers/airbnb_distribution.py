"""Airbnb price distribution visualizer.

This module creates visualizations showing Airbnb price distributions
at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class AirbnbDistributionVisualizer(Visualizer):
    """Create visualizations for Airbnb price distributions.

    Shows Airbnb prices aggregated at both census tract and community area
    levels to demonstrate the hierarchical spatial aggregation.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the Airbnb distribution visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "airbnb_distribution_visualization",
            "Create visualizations for Airbnb price distributions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create Airbnb distribution visualizations."""
        logger.info("Creating Airbnb distribution visualizations...")

        tract_data = context.get("airbnb_tract_data")

        if tract_data is None:
            logger.warning("No Airbnb tract data available for visualization")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago Airbnb Price Distribution Analysis",
            fontsize=18,
            fontweight="bold",
            y=0.98,  # Move title higher
        )

        # 1. Tract-level Airbnb price distribution
        if tract_data is not None and "price_numeric_mean" in tract_data.columns:
            tract_prices = tract_data["price_numeric_mean"].dropna()
            axes[0, 0].hist(
                tract_prices,
                bins=30,
                alpha=0.7,
                color="lightcoral",
                edgecolor="black",
            )
            axes[0, 0].axvline(
                tract_prices.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: ${tract_prices.median():.0f}",
            )
            axes[0, 0].set_xlabel("Average Airbnb Price ($)", fontsize=12)
            axes[0, 0].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 0].set_title(
                f"Census Tract Level (n={len(tract_prices)})", fontsize=14
            )
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # 2. Airbnb units density distribution
        if tract_data is not None and "airbnb_density" in tract_data.columns:
            tract_density = tract_data["airbnb_density"].dropna()
            axes[0, 1].hist(
                tract_density,
                bins=30,
                alpha=0.7,
                color="skyblue",
                edgecolor="black",
            )
            axes[0, 1].axvline(
                tract_density.median(),
                color="blue",
                linestyle="--",
                linewidth=2,
                label=f"Median: {tract_density.median():.1f} units/km²",
            )
            axes[0, 1].set_xlabel("Airbnb Units Density (per km²)", fontsize=12)
            axes[0, 1].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 1].set_title(
                f"Airbnb Units Density Distribution (n={len(tract_density)})",
                fontsize=14,
            )
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()

        # 3. Price vs Units Density scatter plot
        if (
            tract_data is not None
            and "price_numeric_mean" in tract_data.columns
            and "airbnb_density" in tract_data.columns
        ):
            tract_prices = tract_data["price_numeric_mean"].dropna()
            tract_density = tract_data["airbnb_density"].dropna()

            # Merge on tract_geoid to align data
            price_density_data = tract_data[
                ["tract_geoid", "price_numeric_mean", "airbnb_density"]
            ].dropna()

            if len(price_density_data) > 0:
                axes[1, 0].scatter(
                    price_density_data["airbnb_density"],
                    price_density_data["price_numeric_mean"],
                    alpha=0.6,
                    color="purple",
                    s=20,
                )
                axes[1, 0].set_xlabel("Airbnb Units Density (per km²)", fontsize=12)
                axes[1, 0].set_ylabel("Average Airbnb Price ($)", fontsize=12)
                axes[1, 0].set_title("Price vs Units Density Relationship", fontsize=14)
                axes[1, 0].grid(True, alpha=0.3)

        # 4. Statistical summary
        axes[1, 1].axis("off")
        stats_lines = ["Airbnb Analysis Statistics\n" + "=" * 40 + "\n"]

        if tract_data is not None:
            if "price_numeric_mean" in tract_data.columns:
                tract_prices = tract_data["price_numeric_mean"].dropna()
                stats_lines.append("AIRBNB PRICE ANALYSIS:")
                stats_lines.append(f"  Count: {len(tract_prices)}")
                stats_lines.append(f"  Mean: ${tract_prices.mean():.2f}")
                stats_lines.append(f"  Median: ${tract_prices.median():.2f}")
                stats_lines.append(f"  Std Dev: ${tract_prices.std():.2f}")
                stats_lines.append(f"  Min: ${tract_prices.min():.2f}")
                stats_lines.append(f"  Max: ${tract_prices.max():.2f}")
                stats_lines.append("")

            if "airbnb_density" in tract_data.columns:
                tract_density = tract_data["airbnb_density"].dropna()
                stats_lines.append("AIRBNB DENSITY ANALYSIS:")
                stats_lines.append(f"  Count: {len(tract_density)}")
                stats_lines.append(f"  Mean: {tract_density.mean():.2f} units/km²")
                stats_lines.append(f"  Median: {tract_density.median():.2f} units/km²")
                stats_lines.append(f"  Std Dev: {tract_density.std():.2f}")
                stats_lines.append(f"  Min: {tract_density.min():.2f}")
                stats_lines.append(f"  Max: {tract_density.max():.2f}")
                stats_lines.append("")

            if "airbnb_count" in tract_data.columns:
                tract_count = tract_data["airbnb_count"].dropna()
                stats_lines.append("AIRBNB LISTING COUNTS:")
                stats_lines.append(f"  Total tracts with listings: {len(tract_count)}")
                stats_lines.append(f"  Total listings: {tract_count.sum():.0f}")
                stats_lines.append(f"  Mean per tract: {tract_count.mean():.1f}")
                stats_lines.append(f"  Max per tract: {tract_count.max():.0f}")

        stats_text = "\n".join(stats_lines)

        axes[1, 1].text(
            0.05,
            0.95,
            stats_text,
            transform=axes[1, 1].transAxes,
            fontsize=11,
            verticalalignment="top",
            fontfamily="monospace",
            bbox={"boxstyle": "round,pad=0.8", "facecolor": "lightblue", "alpha": 0.8},
        )

        plt.tight_layout()
        plt.subplots_adjust(top=0.85)  # Increase space for title

        # Save the plot
        output_path = Path(self.output_dir) / "airbnb_distribution_analysis.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.close()

        return {"airbnb_distribution_plot": str(output_path)}
