"""Difference-in-Differences trends visualizer.

This module creates visualizations for DiD analysis including adoption curves,
parallel trends plots, an event study, and pre-treatment balance comparisons.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)


class DIDTrendsVisualizer(Visualizer):
    """Create visualizations for DiD trend analysis.

    1. Adoption curve: Cumulative number of tracts treated over time
    2. Parallel trends plot: Average rental prices for treated vs. control over time
    3. Pre-treatment balance comparison: Distribution comparison before treatment
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DiD trends visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "did_trends_visualization",
            "Create visualizations for difference-in-differences trend analysis",
        )
        self.output_dir = output_dir or "output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create DiD trend visualizations."""
        logger.info("Creating DiD trend visualizations...")

        did_panel = context.get("did_panel")

        # Identify ever-treated vs never-treated tracts
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index
        did_panel["ever_treated"] = did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)

        # Create output directory
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 1. Adoption curve plot
        self._create_adoption_curve(did_panel, output_path)

        # 2. Parallel trends plot
        self._create_parallel_trends_plot(did_panel, output_path)

        # 3. Pre-treatment balance comparison
        self._create_pre_treatment_balance_plot(did_panel, output_path)

        # 4. Event study plot (months since treatment)
        self._create_event_study_plot(did_panel, output_path)

        logger.info("All DiD trend visualizations saved to %s", output_path)

        return {
            "adoption_curve_path": str(output_path / "did_adoption_curve.png"),
            "parallel_trends_path": str(output_path / "did_parallel_trends.png"),
            "pre_treatment_balance_path": str(output_path / "did_pre_treatment_balance.png"),
            "event_study_path": str(output_path / "did_event_study.png"),
        }

    def _create_adoption_curve(self, did_panel: pd.DataFrame, output_path: Path) -> None:
        """Create adoption curve showing number of treated tracts over time."""
        # Count number of treated tracts by month
        treated_by_month = (
            did_panel[did_panel["treated"] == 1]
            .groupby("month")["tract_geoid"]
            .nunique()
        )

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 5))
        treated_by_month.plot(ax=ax)
        ax.set_ylabel("Number of Treated Tracts")
        ax.set_xlabel("Date")
        ax.set_title("STR Prohibition Adoption Over Time")

        plt.tight_layout()
        fig.savefig(output_path / "did_adoption_curve.png", dpi=300, bbox_inches="tight")
        logger.info("Saved adoption curve to %s", output_path / "did_adoption_curve.png")
        plt.close(fig)

    def _create_parallel_trends_plot(self, did_panel: pd.DataFrame, output_path: Path) -> None:
        """Create parallel trends plot showing average rent by group over time."""
        # Calculate average rent by month and ever_treated status
        avg_by_group = (
            did_panel.groupby(["month", "ever_treated"])["rental_price"]
            .mean()
            .unstack()
        )
        avg_by_group.columns = ["Never Treated", "Eventually Treated"]

        # Find first treatment date for vertical line
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot both groups
        avg_by_group.plot(ax=ax, alpha=0.7)

        # Add vertical line at first treatment
        if pd.notna(first_treatment):
            ax.axvline(first_treatment, color='red', linestyle='--', label='First Treatment')

        ax.set_ylabel("Average Rental Price ($)")
        ax.set_xlabel("Date")
        ax.set_title("Parallel Trends Plot")
        ax.legend()

        plt.tight_layout()
        fig.savefig(output_path / "did_parallel_trends.png", dpi=300, bbox_inches="tight")
        logger.info("Saved parallel trends plot to %s", output_path / "did_parallel_trends.png")
        plt.close(fig)

    def _create_event_study_plot(self, did_panel: pd.DataFrame, output_path: Path) -> None:
        """Create event study plot showing average rent by months since treatment."""
        # For treated tracts: use months_since_treatment
        treated_panel = did_panel[did_panel["months_since_treatment"].notna()].copy()
        
        # Calculate average rent by months_since_treatment for treated tracts
        avg_treated = treated_panel.groupby("months_since_treatment")["rental_price"].mean()
        
        # For never-treated tracts: calculate overall average as reference
        never_treated_panel = did_panel[did_panel["ever_treated"] == 0]
        never_treated_avg = never_treated_panel["rental_price"].mean()

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot treated tracts by months since treatment
        ax.plot(avg_treated.index, avg_treated.values, alpha=0.7, label='Treated Tracts', linewidth=2)
        
        # Add horizontal reference line for never-treated tracts
        ax.axhline(never_treated_avg, color='steelblue', linestyle='--', alpha=0.7, label=f'Never Treated (Avg: ${never_treated_avg:.0f})')

        # Add vertical line at treatment (months_since_treatment = 0)
        ax.axvline(0, color='red', linestyle='--', alpha=0.7, label='Treatment')

        ax.set_ylabel("Average Rental Price ($)")
        ax.set_xlabel("Months Since Treatment")
        ax.set_title("Event Study: Rental Prices by Months Since Treatment")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.savefig(output_path / "did_event_study.png", dpi=300, bbox_inches="tight")
        logger.info("Saved event study plot to %s", output_path / "did_event_study.png")
        plt.close(fig)

    def _create_pre_treatment_balance_plot(self, did_panel: pd.DataFrame, output_path: Path) -> None:
        """Create pre-treatment balance comparison plot."""
        # Define pre-treatment period
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
        pre_period = did_panel[did_panel["month"] < first_treatment].copy()

        # Get pre-treatment rental prices by group
        never_treated_prices = pre_period.loc[pre_period["ever_treated"] == 0, "rental_price"]
        eventually_treated_prices = pre_period.loc[pre_period["ever_treated"] == 1, "rental_price"]

        # Perform t-test
        t_stat, p_value = stats.ttest_ind(never_treated_prices, eventually_treated_prices)

        # Create figure with subplots
        fig = plt.figure(figsize=(16, 6))
        gs = fig.add_gridspec(1, 3, width_ratios=[2, 2, 1], hspace=0.3, wspace=0.3)

        # 1. Histogram comparison
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.hist(
            never_treated_prices,
            bins=40,
            alpha=0.6,
            color="steelblue",
            label="Never Treated",
            edgecolor="black",
            linewidth=0.5,
        )
        ax1.hist(
            eventually_treated_prices,
            bins=40,
            alpha=0.6,
            color="coral",
            label="Eventually Treated",
            edgecolor="black",
            linewidth=0.5,
        )
        ax1.axvline(
            never_treated_prices.mean(),
            color="steelblue",
            linestyle="--",
            linewidth=2,
            label=f"Never Treated Mean: ${never_treated_prices.mean():.0f}",
        )
        ax1.axvline(
            eventually_treated_prices.mean(),
            color="coral",
            linestyle="--",
            linewidth=2,
            label=f"Eventually Treated Mean: ${eventually_treated_prices.mean():.0f}",
        )
        ax1.set_xlabel("Rental Price ($)", fontsize=11)
        ax1.set_ylabel("Frequency", fontsize=11)
        ax1.set_title("Pre-Treatment Rental Price Distributions", fontsize=12, fontweight="bold")
        ax1.legend(loc="best", fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        # 2. Box plot comparison
        ax2 = fig.add_subplot(gs[0, 1])
        box_data = [never_treated_prices, eventually_treated_prices]
        bp = ax2.boxplot(
            box_data,
            labels=["Never Treated", "Eventually Treated"],
            patch_artist=True,
            showmeans=True,
        )
        bp["boxes"][0].set_facecolor("steelblue")
        bp["boxes"][0].set_alpha(0.6)
        bp["boxes"][1].set_facecolor("coral")
        bp["boxes"][1].set_alpha(0.6)
        ax2.set_ylabel("Rental Price ($)", fontsize=11)
        ax2.set_title("Pre-Treatment Rental Price Box Plots", fontsize=12, fontweight="bold")
        ax2.grid(True, alpha=0.3, axis="y")
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        # 3. Summary statistics text
        ax3 = fig.add_subplot(gs[0, 2])
        ax3.axis("off")

        stats_text = (
            "NEVER TREATED:\n"
            f"  N: {len(never_treated_prices):,}\n"
            f"  Mean: ${never_treated_prices.mean():.2f}\n"
            f"  Std: ${never_treated_prices.std():.2f}\n"
            f"  Median: ${never_treated_prices.median():.2f}\n\n"
            "EVENTUALLY TREATED:\n"
            f"  N: {len(eventually_treated_prices):,}\n"
            f"  Mean: ${eventually_treated_prices.mean():.2f}\n"
            f"  Std: ${eventually_treated_prices.std():.2f}\n"
            f"  Median: ${eventually_treated_prices.median():.2f}\n\n"
            "T-TEST:\n"
            f"  t-statistic: {t_stat:.2f}\n"
            f"  p-value: {p_value:.4f}\n"
            f"  Difference: ${eventually_treated_prices.mean() - never_treated_prices.mean():.2f}\n"
            f"  (% Difference: {((eventually_treated_prices.mean() / never_treated_prices.mean() - 1) * 100):.1f}%)"
        )

        ax3.text(
            0.5,
            0.5,
            stats_text,
            transform=ax3.transAxes,
            fontsize=10,
            verticalalignment="center",
            horizontalalignment="left",
            fontfamily="monospace",
            bbox={"boxstyle": "round,pad=0.8", "facecolor": "lightyellow", "alpha": 0.8},
        )

        fig.suptitle("Pre-Treatment Balance Comparison", fontsize=14, fontweight="bold", y=0.98)

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(output_path / "did_pre_treatment_balance.png", dpi=300, bbox_inches="tight")
        logger.info("Saved pre-treatment balance plot to %s", output_path / "did_pre_treatment_balance.png")
        plt.close(fig)
