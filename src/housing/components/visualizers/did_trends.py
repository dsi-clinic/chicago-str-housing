"""Visualization for DiD descriptive analysis.

This module creates diagnostic plots for Difference-in-Differences analysis
including adoption curves, parallel trends checks, and balance comparisons.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DIDTrendsVisualizer(Visualizer):
    """Create diagnostic visualizations for DiD analysis.

    This visualizer creates:
    1. Treatment adoption curve over time
    2. Parallel trends plot (treated vs. control)
    3. Pre-treatment balance comparison
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DID trends visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "did_trends_visualization",
            "Create diagnostic plots for DiD analysis",
        )
        self.output_dir = Path(output_dir or "/project/output")
        self.required_data = [
            "did_panel",
            "cumulative_adoption",
            "avg_by_group_month",
            "first_treatment_date",
        ]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create DiD diagnostic visualizations.

        Required context keys:
            - did_panel: DataFrame with DiD panel data (including ever_treated)
            - cumulative_adoption: DataFrame with cumulative treated tracts by month
            - avg_by_group_month: DataFrame with average rents by group and month
            - first_treatment_date: Date of first treatment

        Returns:
            Dictionary with paths to saved visualizations
        """
        logger.info("Creating DiD diagnostic visualizations...")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create individual plots
        adoption_path = self._plot_adoption_curve(context)
        trends_path = self._plot_parallel_trends(context)
        combined_path = self._plot_combined_diagnostic(context)

        logger.info("DiD visualizations saved to: %s", self.output_dir)

        return {
            "did_adoption_plot": str(adoption_path),
            "did_trends_plot": str(trends_path),
            "did_diagnostic_plot": str(combined_path),
        }

    def _plot_adoption_curve(self, context: dict[str, Any]) -> Path:
        """Plot cumulative treatment adoption over time."""
        cumulative = context["cumulative_adoption"]
        first_treatment = context["first_treatment_date"]

        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot cumulative adoption
        ax.plot(
            cumulative.index,
            cumulative["cumulative_treated"],
            linewidth=2,
            color="#2ecc71",
        )
        ax.fill_between(
            cumulative.index,
            cumulative["cumulative_treated"],
            alpha=0.3,
            color="#2ecc71",
        )

        # Add vertical line at first treatment
        ax.axvline(
            first_treatment,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"First Treatment ({first_treatment.strftime('%Y-%m')})",
        )

        ax.set_ylabel("Cumulative Treated Tracts", fontsize=12)
        ax.set_xlabel("Month", fontsize=12)
        ax.set_title(
            "STR Prohibition Adoption Over Time", fontsize=14, fontweight="bold"
        )
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)

        # Rotate x-axis labels
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save
        output_path = self.output_dir / "did_adoption_curve.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info("  Saved adoption curve: %s", output_path)
        return output_path

    def _plot_parallel_trends(self, context: dict[str, Any]) -> Path:
        """Plot parallel trends check for treated vs. control groups."""
        avg_by_group = context["avg_by_group_month"]
        first_treatment = context["first_treatment_date"]

        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot both groups
        ax.plot(
            avg_by_group.index,
            avg_by_group["Never Treated"],
            linewidth=2,
            color="#3498db",
            label="Never Treated (Control)",
        )
        ax.plot(
            avg_by_group.index,
            avg_by_group["Eventually Treated"],
            linewidth=2,
            color="#e74c3c",
            label="Eventually Treated",
        )

        # Add vertical line at first treatment
        ax.axvline(
            first_treatment,
            color="gray",
            linestyle="--",
            linewidth=1.5,
            label=f"First Treatment ({first_treatment.strftime('%Y-%m')})",
        )

        # Shade pre-treatment period
        ax.axvspan(
            avg_by_group.index.min(),
            first_treatment,
            alpha=0.1,
            color="gray",
            label="Pre-Treatment Period",
        )

        ax.set_ylabel("Average Rental Price ($)", fontsize=12)
        ax.set_xlabel("Month", fontsize=12)
        ax.set_title(
            "Parallel Trends Check: Treated vs. Control Tracts",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)

        # Rotate x-axis labels
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save
        output_path = self.output_dir / "did_parallel_trends.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info("  Saved parallel trends plot: %s", output_path)
        return output_path

    def _plot_combined_diagnostic(self, context: dict[str, Any]) -> Path:
        """Create combined diagnostic figure with multiple panels."""
        did_panel = context["did_panel"]
        cumulative = context["cumulative_adoption"]
        avg_by_group = context["avg_by_group_month"]
        first_treatment = context["first_treatment_date"]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Panel 1: Adoption curve
        ax1 = axes[0, 0]
        ax1.plot(
            cumulative.index,
            cumulative["cumulative_treated"],
            linewidth=2,
            color="#2ecc71",
        )
        ax1.fill_between(
            cumulative.index,
            cumulative["cumulative_treated"],
            alpha=0.3,
            color="#2ecc71",
        )
        ax1.axvline(first_treatment, color="red", linestyle="--", linewidth=1.5)
        ax1.set_ylabel("Cumulative Treated Tracts")
        ax1.set_xlabel("Month")
        ax1.set_title("A. Treatment Adoption Over Time", fontweight="bold")
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis="x", rotation=45)

        # Panel 2: Parallel trends
        ax2 = axes[0, 1]
        ax2.plot(
            avg_by_group.index,
            avg_by_group["Never Treated"],
            linewidth=2,
            color="#3498db",
            label="Never Treated",
        )
        ax2.plot(
            avg_by_group.index,
            avg_by_group["Eventually Treated"],
            linewidth=2,
            color="#e74c3c",
            label="Eventually Treated",
        )
        ax2.axvline(first_treatment, color="gray", linestyle="--", linewidth=1.5)
        ax2.axvspan(avg_by_group.index.min(), first_treatment, alpha=0.1, color="gray")
        ax2.set_ylabel("Average Rental Price ($)")
        ax2.set_xlabel("Month")
        ax2.set_title("B. Parallel Trends Check", fontweight="bold")
        ax2.legend(loc="upper left", fontsize=9)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis="x", rotation=45)

        # Panel 3: Pre-treatment rent distribution
        ax3 = axes[1, 0]
        pre_period = did_panel[did_panel["month"] < first_treatment]

        never_treated_rents = pre_period[pre_period["ever_treated"] == 0][
            "rental_price"
        ]
        eventually_treated_rents = pre_period[pre_period["ever_treated"] == 1][
            "rental_price"
        ]

        ax3.hist(
            never_treated_rents,
            bins=30,
            alpha=0.6,
            label="Never Treated",
            color="#3498db",
            density=True,
        )
        ax3.hist(
            eventually_treated_rents,
            bins=30,
            alpha=0.6,
            label="Eventually Treated",
            color="#e74c3c",
            density=True,
        )
        ax3.set_xlabel("Rental Price ($)")
        ax3.set_ylabel("Density")
        ax3.set_title("C. Pre-Treatment Rent Distribution", fontweight="bold")
        ax3.legend(loc="upper right", fontsize=9)
        ax3.grid(True, alpha=0.3)

        # Panel 4: Treatment timing histogram
        ax4 = axes[1, 1]

        # Get first treatment date for each tract
        treatment_dates = (
            did_panel[did_panel["treated"] == 1].groupby("tract_geoid")["month"].min()
        )

        ax4.hist(
            treatment_dates, bins=30, color="#9b59b6", alpha=0.7, edgecolor="white"
        )
        ax4.set_xlabel("Treatment Date")
        ax4.set_ylabel("Number of Tracts")
        ax4.set_title("D. Distribution of Treatment Timing", fontweight="bold")
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis="x", rotation=45)

        # Overall title
        fig.suptitle(
            "DiD Diagnostic Analysis: STR Prohibition Effects",
            fontsize=16,
            fontweight="bold",
            y=1.02,
        )

        plt.tight_layout()

        # Save
        output_path = self.output_dir / "did_diagnostic_analysis.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info("  Saved combined diagnostic: %s", output_path)
        return output_path
