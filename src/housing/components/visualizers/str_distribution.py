"""STR prohibition distribution visualizer.

This module creates visualizations showing STR prohibition distributions
at census tract level.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRDistributionVisualizer(Visualizer):
    """Create visualizations for STR prohibition distributions.

    Shows STR prohibition data aggregated at census tract level
    to demonstrate spatial patterns.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR distribution visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_distribution_visualization",
            "Create visualizations for STR prohibition distributions",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR distribution visualizations."""
        logger.info("Creating STR distribution visualizations...")

        tract_data = context.get("str_tract_data")

        if tract_data is None:
            logger.warning("No STR tract data available for visualization")
            return {}

        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            "Chicago STR Prohibition Distribution Analysis",
            fontsize=18,
            fontweight="bold",
            y=0.98,  # Move title higher
        )

        # 1. STR prohibition density distribution
        if "point_density" in tract_data.columns:
            tract_density = tract_data["point_density"].dropna()
            axes[0, 0].hist(
                tract_density,
                bins=30,
                alpha=0.7,
                color="orange",
                edgecolor="black",
            )
            axes[0, 0].axvline(
                tract_density.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: {tract_density.median():.1f} prohibitions/km²",
            )
            axes[0, 0].set_xlabel("STR Prohibition Density (per km²)", fontsize=12)
            axes[0, 0].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 0].set_title(
                f"STR Prohibition Density Distribution (n={len(tract_density)})",
                fontsize=14,
            )
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # 2. Prohibited units distribution
        if "number_of_units_sum" in tract_data.columns:
            tract_units = tract_data["number_of_units_sum"].dropna()
            axes[0, 1].hist(
                tract_units,
                bins=30,
                alpha=0.7,
                color="lightcoral",
                edgecolor="black",
            )
            axes[0, 1].axvline(
                tract_units.median(),
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Median: {tract_units.median():.0f} units",
            )
            axes[0, 1].set_xlabel("Total Prohibited Units", fontsize=12)
            axes[0, 1].set_ylabel("Number of Census Tracts", fontsize=12)
            axes[0, 1].set_title(
                f"Prohibited Units Distribution (n={len(tract_units)})", fontsize=14
            )
            axes[0, 1].grid(True, alpha=0.3)
            axes[0, 1].legend()

        # 3. Density vs Units scatter plot
        if (
            "point_density" in tract_data.columns
            and "number_of_units_sum" in tract_data.columns
        ):
            density_units_data = tract_data[
                ["point_density", "number_of_units_sum"]
            ].dropna()

            if len(density_units_data) > 0:
                axes[1, 0].scatter(
                    density_units_data["point_density"],
                    density_units_data["number_of_units_sum"],
                    alpha=0.6,
                    color="darkorange",
                    s=20,
                )
                axes[1, 0].set_xlabel("STR Prohibition Density (per km²)", fontsize=12)
                axes[1, 0].set_ylabel("Total Prohibited Units", fontsize=12)
                axes[1, 0].set_title("Density vs Units Relationship", fontsize=14)
                axes[1, 0].grid(True, alpha=0.3)

        # 4. Statistical summary
        axes[1, 1].axis("off")
        stats_lines = ["STR Prohibition Analysis Statistics\n" + "=" * 50 + "\n"]

        if tract_data is not None:
            if "point_density" in tract_data.columns:
                tract_density = tract_data["point_density"].dropna()
                stats_lines.append("STR PROHIBITION DENSITY:")
                stats_lines.append(f"  Count: {len(tract_density)}")
                stats_lines.append(
                    f"  Mean: {tract_density.mean():.2f} prohibitions/km²"
                )
                stats_lines.append(
                    f"  Median: {tract_density.median():.2f} prohibitions/km²"
                )
                stats_lines.append(f"  Std Dev: {tract_density.std():.2f}")
                stats_lines.append(f"  Min: {tract_density.min():.2f}")
                stats_lines.append(f"  Max: {tract_density.max():.2f}")
                stats_lines.append("")

            if "number_of_units_sum" in tract_data.columns:
                tract_units = tract_data["number_of_units_sum"].dropna()
                stats_lines.append("PROHIBITED UNITS:")
                stats_lines.append(f"  Count: {len(tract_units)}")
                stats_lines.append(f"  Mean: {tract_units.mean():.0f} units")
                stats_lines.append(f"  Median: {tract_units.median():.0f} units")
                stats_lines.append(f"  Std Dev: {tract_units.std():.0f}")
                stats_lines.append(f"  Min: {tract_units.min():.0f}")
                stats_lines.append(f"  Max: {tract_units.max():.0f}")
                stats_lines.append("")

            if "point_count" in tract_data.columns:
                tract_count = tract_data["point_count"].dropna()
                stats_lines.append("STR PROHIBITION COUNTS:")
                stats_lines.append(
                    f"  Total tracts with prohibitions: {len(tract_count)}"
                )
                stats_lines.append(
                    f"  Total prohibition buildings: {tract_count.sum():.0f}"
                )
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
            bbox={
                "boxstyle": "round,pad=0.8",
                "facecolor": "lightyellow",
                "alpha": 0.8,
            },
        )

        plt.tight_layout()
        plt.subplots_adjust(top=0.85)  # Increase space for title

        # Save the plot
        output_path = Path(self.output_dir) / "str_distribution_analysis.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved visualization to: %s", output_path)

        plt.close()

        return {"str_distribution_plot": str(output_path)}
