import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRBuildingsDensityDistributionVisualizer(Visualizer):
    """Visualizations for STR buildings distributions (density), ignoring zero-density entries."""

    def __init__(self, output_dir: str | None = None) -> None:
        super().__init__(
            "str_buildings_density_distribution_visualization",
            "Create visualizations for STR buildings density distributions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("Creating STR buildings density distribution visualizations...")

        tract_data = context.get("str_buildings_tract_data")
        community_data = context.get("str_buildings_community_data")

        if tract_data is None and community_data is None:
            logger.warning("No STR data available for visualization")
            return {}

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago STR Buildings Density Distribution (Not Including Zeroes)",
            fontsize=18,
            fontweight="bold",
        )

        # Tract-level
        if tract_data is not None:
            # Drop zero densities
            tract_densities = tract_data["str_buildings_density"].dropna()
            tract_densities = tract_densities[tract_densities > 0]

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
                label=f"Median: {tract_densities.median():.0f}",
            )
            axes[0, 0].set_xlabel("STR Buildings Point Density", fontsize=12)
            axes[0, 0].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 0].set_title(
                f"Census Tract Level (n={len(tract_densities)})", fontsize=14
            )
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # Community-level
        if community_data is not None:
            community_densities = community_data["str_buildings_density"].dropna()
            community_densities = community_densities[community_densities > 0]

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
                label=f"Median: {community_densities.median():.0f}",
            )
            axes[0, 1].set_xlabel("STR Buildings Point Density", fontsize=12)
            axes[0, 1].set_ylabel("Number of Community Areas", fontsize=12)
            axes[0, 1].set_title(
                f"Community Area Level (n={len(community_densities)})", fontsize=14
            )
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()

        # Box plots
        if tract_data is not None and community_data is not None:
            box_data = [tract_densities, community_densities]
            bp = axes[1, 0].boxplot(
                box_data,
                labels=["Census Tract", "Community Area"],
                patch_artist=True,
                showmeans=True,
                meanline=True,
            )
            bp["boxes"][0].set_facecolor("steelblue")
            bp["boxes"][1].set_facecolor("forestgreen")
            axes[1, 0].set_ylabel(
                "STR Buildings Point Density (listings/km²)", fontsize=12
            )
            axes[1, 0].set_title(
                "STR Buildings Density Comparison (listings/km²)", fontsize=14
            )
            axes[1, 0].grid(True, alpha=0.3, axis="y")

        # Statistical summary
        axes[1, 1].axis("off")
        stats_lines = ["STR Buildings Statistics (excluding zeros)\n" + "=" * 50 + "\n"]

        if tract_data is not None:
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

        if community_data is not None:
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
            Path(self.output_dir) / "str_buildings_density_distribution_analysis.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)
        plt.close()

        return {"str_buildings_density_distribution_plot": str(output_path)}
