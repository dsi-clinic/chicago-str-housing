"""STR units count distribution visualizer.

This module creates visualizations showing STR units count distributions
at both tract and community area levels.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRUnitsCountDistributionVisualizer(Visualizer):
    """Create visualizations for STR units distributions.

    Shows STR units list aggregated at both census tract and community area
    levels to demonstrate the hierarchical spatial aggregation.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR units distribution visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_units_count_distribution_visualization",
            "Create visualizations for STR units count distributions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR units count distribution visualizations."""
        logger.info("Creating STR units count distribution visualizations...")

        tract_data = context.get("str_units_tract_data")
        community_data = context.get("str_units_community_data")

        if tract_data is None and community_data is None:
            logger.warning("No STR data available for visualization")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago STR Units Count Distribution: Tract vs Community Area",
            fontsize=18,
            fontweight="bold",
        )

        # 1. Tract-level STR units count distribution
        if tract_data is not None:
            tract_counts = tract_data["str_units_count"].dropna()
            axes[0, 0].hist(
                tract_counts,
                bins=30,
                alpha=0.7,
                color="steelblue",
                edgecolor="black",
            )
            axes[0, 0].axvline(
                tract_counts.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: {tract_counts.median():.0f}",
            )
            axes[0, 0].set_xlabel("STR Units Point Count", fontsize=12)
            axes[0, 0].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 0].set_title(
                f"Census Tract Level (n={len(tract_counts)})", fontsize=14
            )
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # 2. Community-level STR units count distribution
        if community_data is not None:
            community_counts = community_data["str_units_count"].dropna()
            axes[0, 1].hist(
                community_counts,
                bins=20,
                alpha=0.7,
                color="forestgreen",
                edgecolor="black",
            )
            axes[0, 1].axvline(
                community_counts.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: {community_counts.median():.0f}",
            )
            axes[0, 1].set_xlabel("STR Units Point Count", fontsize=12)
            axes[0, 1].set_ylabel("Number of Community Areas", fontsize=12)
            axes[0, 1].set_title(
                f"Community Area Level (n={len(community_counts)})", fontsize=14
            )
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()

        # 3. Box plots for STR units densities
        if tract_data is not None and community_data is not None:
            tract_counts = tract_data["str_units_count"].dropna()
            community_counts = community_data["str_units_count"].dropna()

            box_data = [tract_counts, community_counts]
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

            axes[1, 0].set_ylabel("STR Units Point Count", fontsize=12)
            axes[1, 0].set_title("STR Units Count Comparison", fontsize=14)
            axes[1, 0].grid(True, alpha=0.3, axis="y")

        # 4. Statistical summary
        axes[1, 1].axis("off")
        stats_lines = ["STR Units Statistics\n" + "=" * 40 + "\n"]

        if tract_data is not None:
            tract_counts = tract_data["str_units_count"].dropna()
            stats_lines.append("CENSUS TRACT LEVEL:")
            stats_lines.append(f"  Count: {len(tract_counts)}")
            stats_lines.append(f"  Mean: {tract_counts.mean():.2f}")
            stats_lines.append(f"  Median: {tract_counts.median():.2f}")
            stats_lines.append(f"  Std Dev: {tract_counts.std():.2f}")
            stats_lines.append(f"  Min: {tract_counts.min():.2f}")
            stats_lines.append(f"  Max: {tract_counts.max():.2f}")
            stats_lines.append(f"  Q1: {tract_counts.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: {tract_counts.quantile(0.75):.2f}")
            stats_lines.append("")

        if community_data is not None:
            community_counts = community_data["str_units_count"].dropna()
            stats_lines.append("COMMUNITY AREA LEVEL:")
            stats_lines.append(f"  Count: {len(community_counts)}")
            stats_lines.append(f"  Mean: {community_counts.mean():.2f}")
            stats_lines.append(f"  Median: {community_counts.median():.2f}")
            stats_lines.append(f"  Std Dev: {community_counts.std():.2f}")
            stats_lines.append(f"  Min: {community_counts.min():.2f}")
            stats_lines.append(f"  Max: {community_counts.max():.2f}")
            stats_lines.append(f"  Q1: {community_counts.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: {community_counts.quantile(0.75):.2f}")

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
            Path(self.output_dir) / "str_units_count_distribution_analysis.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)
        plt.close()

        return {"str_count_distribution_plot": str(output_path)}
