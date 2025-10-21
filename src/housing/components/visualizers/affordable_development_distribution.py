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


class AffordableDistributionVisualizer(Visualizer):
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

        tract_data = context.get("affordable_developments_tract_data")
        # community_data = context.get("affordable_developments_community_data")

        if tract_data is None:
            logger.warning("No tract level data available for visualization")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago Affordable Housing Distribution: by Tract",
            fontsize=18,
            fontweight="bold",
        )

        # 1. Tract-level unit density distribution
        if tract_data is not None:
            tract_unit_density = tract_data["unit_density"].dropna()
            axes[0, 0].hist(
                tract_unit_density,
                bins=30,
                alpha=0.7,
                color="steelblue",
                edgecolor="black",
            )
            axes[0, 0].axvline(
                tract_unit_density.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: ${tract_unit_density.median():.0f}",
            )
            axes[0, 0].set_xlabel("Tract Unit Density (Units/km2)", fontsize=12)
            axes[0, 0].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 0].set_title(
                f"Unit Density by Census Tract (n={len(tract_unit_density)})",
                fontsize=14,
            )
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # 2. Tract-level number of units distribution
        if tract_data is not None:
            tract_units = tract_data["units_sum"].dropna()
            axes[0, 1].hist(
                tract_units,
                bins=20,
                alpha=0.7,
                color="forestgreen",
                edgecolor="black",
            )
            axes[0, 1].axvline(
                tract_units.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: ${tract_units.median():.0f}",
            )
            axes[0, 1].set_xlabel("Number of Affordable Units", fontsize=12)
            axes[0, 1].set_ylabel("Number of Tracts", fontsize=12)
            axes[0, 1].set_title(
                f"Number of Units by Census Tract (n={len(tract_units)})", fontsize=14
            )
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()

        # 3. Box plots for comparison
        if tract_data is not None:
            ax = axes[1, 0]
            # First boxplot (left y-axis)
            bp1 = ax.boxplot(
                [tract_unit_density],
                positions=[0],
                widths=0.35,
                patch_artist=True,
                showmeans=True,
                meanline=True,
                labels=["Unit Density"],
            )
            ax.set_ylabel("Unit Density")

            # Second y-axis for the second dataset
            ax2 = ax.twinx()
            bp2 = ax2.boxplot(
                [tract_units],
                positions=[1],
                widths=0.35,
                patch_artist=True,
                showmeans=True,
                meanline=True,
                labels=["Number of Units"],
            )
            ax2.set_ylabel("Number of Units")
            # Color the boxes
            bp1["boxes"][0].set_facecolor("steelblue")
            bp2["boxes"][0].set_facecolor("forestgreen")

            axes[1, 0].set_title(
                "Units & Unit Density Distribution Comparison", fontsize=14
            )
            axes[1, 0].grid(True, alpha=0.3, axis="y")

        # 4. Statistical summary
        axes[1, 1].axis("off")
        stats_lines = ["Affordable Development Units Statistics\n" + "=" * 40 + "\n"]

        if tract_data is not None:
            stats_lines.append("UNIT DENSITY:")
            stats_lines.append(f"  Count: {len(tract_unit_density)}")
            stats_lines.append(f"  Mean: {tract_unit_density.mean():.2f}")
            stats_lines.append(f"  Median: {tract_unit_density.median():.2f}")
            stats_lines.append(f"  Std Dev: {tract_unit_density.std():.2f}")
            stats_lines.append(f"  Min: {tract_unit_density.min():.2f}")
            stats_lines.append(f"  Max: {tract_unit_density.max():.2f}")
            stats_lines.append(f"  Q1: {tract_unit_density.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: {tract_unit_density.quantile(0.75):.2f}")
            stats_lines.append("")

            stats_lines.append("UNIT COUNT:")
            stats_lines.append(f"  Count: {len(tract_units)}")
            stats_lines.append(f"  Mean: {tract_units.mean():.2f}")
            stats_lines.append(f"  Median: {tract_units.median():.2f}")
            stats_lines.append(f"  Std Dev: {tract_units.std():.2f}")
            stats_lines.append(f"  Min: {tract_units.min():.2f}")
            stats_lines.append(f"  Max: {tract_units.max():.2f}")
            stats_lines.append(f"  Q1: {tract_units.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: {tract_units.quantile(0.75):.2f}")

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
        output_path = (
            Path(self.output_dir) / "affordable_development_distribution_analysis.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.close()

        return {"affordable_development_distribution_plot": str(output_path)}
