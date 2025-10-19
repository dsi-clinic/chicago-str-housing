"""STR prohibition visualization module.

Creates visualizations for short-term rental prohibition analysis.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import seaborn as sns

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class STRProhibitionVisualizer(Visualizer):
    """Create visualizations for STR prohibition analysis."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the STR prohibition visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "str_prohibition_visualization",
            "Create visualizations for STR prohibition analysis",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create STR prohibition visualizations."""
        logger.info("Creating STR prohibition visualizations...")

        # Get data from context
        str_tract_analysis = context.get("str_tract_analysis")
        str_correlations = context.get("str_correlations", {})
        str_summary = context.get("str_summary", {})

        if str_tract_analysis is None or len(str_tract_analysis) == 0:
            logger.warning(
                "No STR tract analysis data available, skipping visualization"
            )
            return {}

        # Create figure with subplots
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        fig.suptitle(
            "Chicago Short-Term Rental Prohibition Correlation Analysis",
            fontsize=16,
            fontweight="bold",
        )

        # 1. STR Density vs Rental Price
        ax1 = fig.add_subplot(gs[0, 0])
        if (
            "str_prohibition_density" in str_tract_analysis.columns
            and "avg_rental_price" in str_tract_analysis.columns
        ):
            data_clean = str_tract_analysis[
                ["str_prohibition_density", "avg_rental_price"]
            ].dropna()
            if len(data_clean) > 0:
                ax1.scatter(
                    data_clean["str_prohibition_density"],
                    data_clean["avg_rental_price"],
                    alpha=0.6,
                    s=20,
                )
                ax1.set_xlabel("STR Prohibition Density (per km²)")
                ax1.set_ylabel("Average Rental Price ($)")
                ax1.set_title("STR Density vs Rental Prices")
                ax1.grid(True, alpha=0.3)

        # 2. STR Density vs Airbnb Density
        ax2 = fig.add_subplot(gs[0, 1])
        if (
            "str_prohibition_density" in str_tract_analysis.columns
            and "airbnb_density" in str_tract_analysis.columns
        ):
            data_clean = str_tract_analysis[
                ["str_prohibition_density", "airbnb_density"]
            ].dropna()
            if len(data_clean) > 0:
                ax2.scatter(
                    data_clean["str_prohibition_density"],
                    data_clean["airbnb_density"],
                    alpha=0.6,
                    s=20,
                    color="green",
                )
                ax2.set_xlabel("STR Prohibition Density (per km²)")
                ax2.set_ylabel("Airbnb Density (per km²)")
                ax2.set_title("STR Density vs Airbnb Density")
                ax2.grid(True, alpha=0.3)

        # 3. Comprehensive Correlation Matrix
        ax3 = fig.add_subplot(gs[1, 0])
        # Build correlation matrix including density metrics only
        corr_cols = []
        corr_labels = []

        # Select available columns for correlation matrix - density metrics only
        if "str_prohibition_density" in str_tract_analysis.columns:
            corr_cols.append("str_prohibition_density")
            corr_labels.append("STR\nDensity")
        if "avg_rental_price" in str_tract_analysis.columns:
            corr_cols.append("avg_rental_price")
            corr_labels.append("Rental\nPrice")
        if "airbnb_density" in str_tract_analysis.columns:
            corr_cols.append("airbnb_density")
            corr_labels.append("Airbnb\nDensity")

        min_corr_vars = 2  # Minimum variables for correlation matrix
        min_data_points = 10  # Minimum data points for reliable correlations

        if len(corr_cols) >= min_corr_vars:
            # Calculate correlation matrix
            corr_data = str_tract_analysis[corr_cols].dropna()
            if len(corr_data) > min_data_points:
                corr_matrix = corr_data.corr()

                # Create heatmap with better formatting
                sns.heatmap(
                    corr_matrix,
                    annot=True,
                    fmt=".3f",
                    cmap="RdBu_r",
                    center=0,
                    square=True,
                    ax=ax3,
                    cbar_kws={"shrink": 0.7, "label": "Correlation"},
                    vmin=-1,
                    vmax=1,
                    linewidths=0.5,
                    linecolor="white",
                )

                # Use custom labels for better readability
                ax3.set_xticklabels(corr_labels, rotation=45, ha="right")
                ax3.set_yticklabels(corr_labels, rotation=0)
                ax3.set_title(
                    "Correlation Matrix: STR, Airbnb & Rental", fontsize=11, pad=10
                )
            else:
                ax3.text(0.5, 0.5, "Insufficient data", ha="center", va="center")
                ax3.set_title("Correlation Matrix")
        else:
            ax3.text(
                0.5,
                0.5,
                "Insufficient variables",
                ha="center",
                va="center",
                transform=ax3.transAxes,
            )
            ax3.set_title("Correlation Matrix")
            ax3.axis("off")

        # 4. Summary statistics
        ax4 = fig.add_subplot(gs[1, 1])
        ax4.axis("off")

        stats_lines = ["Statistical Summary\n"]
        stats_lines.append(
            f"Total Buildings: {str_summary.get('total_buildings', 'N/A')}"
        )
        stats_lines.append(
            f"Tracts with Prohibitions: {str_summary.get('tracts_with_prohibitions', 'N/A')}"
        )
        stats_lines.append("")

        if "avg_rent_with_prohibitions" in str_summary:
            stats_lines.append("Average Rent Comparison:")
            stats_lines.append(
                f"  With Prohibitions: ${str_summary['avg_rent_with_prohibitions']:,.0f}"
            )
            stats_lines.append(
                f"  Without Prohibitions: ${str_summary['avg_rent_without_prohibitions']:,.0f}"
            )
            stats_lines.append(f"  Difference: ${str_summary['rent_difference']:,.0f}")
            stats_lines.append("")

        if str_correlations:
            stats_lines.append("Key Correlations (Density Metrics):")
            # Only show density-based correlations
            for name, corr in str_correlations.items():
                if "Density" in name and "Count" not in name and "Units" not in name:
                    stats_lines.append(f"  {name}: {corr:.3f}")

        stats_text = "\n".join(stats_lines)

        ax4.text(
            0.05,
            0.95,
            stats_text,
            transform=ax4.transAxes,
            fontsize=10,
            verticalalignment="top",
            fontfamily="monospace",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "lightgray", "alpha": 0.8},
        )

        # Save the plot
        output_path = Path(self.output_dir) / "str_correlation_analysis.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Saved STR visualization to: %s", output_path)

        plt.close()

        return {"str_visualization_path": str(output_path)}
