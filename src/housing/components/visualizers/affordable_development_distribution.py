"""Rental price distribution visualizer.

This module creates visualizations showing rental price distributions
at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from housing.components.utils import (
    calculate_pairwise_correlation_matrix,
    create_correlation_heatmap,
    create_histogram_with_median,
    create_scatter_with_trend,
)
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
            "affordable_distribution_visualization",
            "Create visualizations for affordable development unit count & density distributions by tract",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create affordable development distribution visualizations."""
        logger.info("Creating affordable development distribution visualizations...")

        tract_data = context.get("affordable_developments_tract_data")

        if tract_data is None:
            logger.warning("No tract level data available for visualization")
            return {}

        # PLOT ONE: UNITS

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago Affordable Housing Development Unit Distribution: by Tract",
            fontsize=18,
            fontweight="bold",
        )

        # 1. Tract-level unit density distribution
        if tract_data is not None:
            tract_unit_density = tract_data[
                "affordable_development_unit_density"
            ].dropna()
            tract_unit_density = tract_unit_density[tract_unit_density > 0]

            create_histogram_with_median(
                ax=axes[0, 0],
                data=tract_unit_density,
                title="Unit Density by Census Tract",
                xlabel="Tract Unit Density (Units/km2)",
                ylabel="Number of Census Tracts",
                median_format="{:.0f}",
            )

        # 2. Tract-level number of units distribution
        if tract_data is not None:
            tract_units = tract_data["units_sum"].dropna()
            create_histogram_with_median(
                ax=axes[0, 1],
                data=tract_units,
                title="Total Units by Census Tract",
                xlabel="Tract Unit Density (Units/km2)",
                ylabel="Number of Census Tracts",
                median_format="{:.0f}",
            )

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
        stats_lines = [
            "Affordable Development Units Statistics (For Nonzero Tracts)\n"
            + "=" * 40
            + "\n"
        ]

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
        units_output_path = (
            Path(self.output_dir) / "affordable_units_distribution_analysis.png"
        )
        units_output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(units_output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", units_output_path)

        plt.close()

        # PLOT TWO: BUILDING VS UNIT DENSITY

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago Affordable Housing Development Building Distribution: by Tract",
            fontsize=18,
            fontweight="bold",
        )

        # 1. Tract-level building density distribution
        if tract_data is not None:
            tract_density = tract_data["affordable_development_density"].dropna()
            tract_density = tract_density[tract_density > 0]

            create_histogram_with_median(
                ax=axes[0, 0],
                data=tract_density,
                title="Affordable Development Building Density by Census Tract",
                xlabel="Tract Development Density (Buildings/km2)",
                ylabel="Number of Census Tracts",
                median_format="{:.0f}",
            )

        # 2. Tract-level unit density distribution
        if tract_data is not None:
            create_histogram_with_median(
                ax=axes[0, 1],
                data=tract_unit_density,
                title="Unit Density by Census Tract",
                xlabel="Tract Unit Density (Units/km2)",
                ylabel="Number of Census Tracts",
                median_format="{:.0f}",
            )

        # 3. Scatterplot of building vs. unit density with trend
        if tract_data is not None:
            create_scatter_with_trend(
                ax=axes[1, 0],
                x_data=tract_density,
                y_data=tract_unit_density,
                title="Building vs. Unit Density for Affordable Housing Developments: Tract-Level Data",
                xlabel="Building Density",
                ylabel="Unit Density",
            )

        # 4. Correlation Matrix (incl. zero-tracts?)
        if tract_data is not None:
            corr = calculate_pairwise_correlation_matrix(
                df=tract_data,
                columns=[
                    "affordable_development_count",
                    "affordable_development_density",
                    "units_sum",
                    "affordable_development_unit_density",
                ],
            )

            create_correlation_heatmap(
                ax=axes[1, 1],
                corr_matrix=corr,
                labels=[
                    "Building Count",
                    "Building Density",
                    "Unit Count",
                    "Unit Density",
                ],
                title="Affordable Development Dataset Correlation Matrix",
            )

        plt.tight_layout()

        # Save the plot
        buildings_output_path = (
            Path(self.output_dir) / "affordable_development_distribution_analysis.png"
        )
        buildings_output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(buildings_output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", buildings_output_path)

        plt.close()

        return {
            "affordable_units_distribution_plot": str(units_output_path),
            "affordable_development_distribution_plot": str(buildings_output_path),
        }
