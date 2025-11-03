"""STR units distribution visualizer.

This module creates visualizations showing STR units density distribution
at both tract and community area levels, excluding zero-unit areas.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRUnitsDensityDistributionVisualizer(Visualizer):
    """Create visualizations for STR units distributions (density).

    Excludes tracts and communities with zero STR units to better
    visualize where listings actually exist.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR units distribution visualizer."""
        super().__init__(
            "str_units_density_distribution_visualization",
            "Create visualizations for STR units density distributions (non-zero only)",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR units density distribution visualizations."""
        logger.info("Creating STR units density distribution visualizations...")

        tract_data = context.get("str_units_tract_data")
        community_data = context.get("str_units_community_data")

        if tract_data is None and community_data is None:
            logger.warning("No STR data available for visualization")
            return {}

        # Filter out zero-unit entries before plotting
        if tract_data is not None and "str_units_count" in tract_data.columns:
            tract_data = tract_data[tract_data["str_units_count"] > 0]
        if community_data is not None and "str_units_count" in community_data.columns:
            community_data = community_data[community_data["str_units_count"] > 0]

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago STR Units Density Distribution (Not Including Zeros)",
            fontsize=18,
            fontweight="bold",
        )

        # Tract-level STR density distribution
        if tract_data is not None and not tract_data.empty:
            tract_densities = tract_data["str_units_density"].dropna()
            axes[0, 0].hist(
                tract_densities,
                bins=30,
                alpha=0.7,
                color="steelblue",
                edgecolor="black",
            )
            axes[0, 0].axvline(
                tract_densities.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: {tract_densities.median():.2f}",
            )
            axes[0, 0].set_xlabel("STR Units Density (listings/km²)", fontsize=12)
            axes[0, 0].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 0].set_title(
                f"Census Tract Level (n={len(tract_densities)})", fontsize=14
            )
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # Community-level STR density distribution
        if community_data is not None and not community_data.empty:
            community_densities = community_data["str_units_density"].dropna()
            axes[0, 1].hist(
                community_densities,
                bins=20,
                alpha=0.7,
                color="forestgreen",
                edgecolor="black",
            )
            axes[0, 1].axvline(
                community_densities.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: {community_densities.median():.2f}",
            )
            axes[0, 1].set_xlabel("STR Units Density (listings/km²)", fontsize=12)
            axes[0, 1].set_ylabel("Number of Community Areas", fontsize=12)
            axes[0, 1].set_title(
                f"Community Area Level (n={len(community_densities)})", fontsize=14
            )
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()

        # Box plots for STR units densities
        if (
            tract_data is not None
            and community_data is not None
            and not tract_data.empty
            and not community_data.empty
        ):
            tract_densities = tract_data["str_units_density"].dropna()
            community_densities = community_data["str_units_density"].dropna()

            box_data = [tract_densities, community_densities]
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

            axes[1, 0].set_ylabel("STR Units Density (listings/km²)", fontsize=12)
            axes[1, 0].set_title(
                "STR Units Density Comparison (Non-zero Only)", fontsize=14
            )
            axes[1, 0].grid(True, alpha=0.3, axis="y")

        # Statistical summary
        axes[1, 1].axis("off")
        stats_lines = ["STR Units Statistics (Non-zero Areas)\n" + "=" * 40 + "\n"]

        if tract_data is not None and not tract_data.empty:
            tract_densities = tract_data["str_units_density"].dropna()
            stats_lines.append("CENSUS TRACT LEVEL:")
            stats_lines.append(f"  Count: {len(tract_densities)}")
            stats_lines.append(f"  Mean: {tract_densities.mean():.2f}")
            stats_lines.append(f"  Median: {tract_densities.median():.2f}")
            stats_lines.append(f"  Std Dev: {tract_densities.std():.2f}")
            stats_lines.append(f"  Min: {tract_densities.min():.2f}")
            stats_lines.append(f"  Max: {tract_densities.max():.2f}")
            stats_lines.append(f"  Q1: {tract_densities.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: {tract_densities.quantile(0.75):.2f}")
            stats_lines.append("")

        if community_data is not None and not community_data.empty:
            community_densities = community_data["str_units_density"].dropna()
            stats_lines.append("COMMUNITY AREA LEVEL:")
            stats_lines.append(f"  Count: {len(community_densities)}")
            stats_lines.append(f"  Mean: {community_densities.mean():.2f}")
            stats_lines.append(f"  Median: {community_densities.median():.2f}")
            stats_lines.append(f"  Std Dev: {community_densities.std():.2f}")
            stats_lines.append(f"  Min: {community_densities.min():.2f}")
            stats_lines.append(f"  Max: {community_densities.max():.2f}")
            stats_lines.append(f"  Q1: {community_densities.quantile(0.25):.2f}")
            stats_lines.append(f"  Q3: {community_densities.quantile(0.75):.2f}")

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
            Path(self.output_dir) / "str_units_density_distribution_nonzero.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)
        plt.close()

        return {"str_units_density_distribution_plot": str(output_path)}
