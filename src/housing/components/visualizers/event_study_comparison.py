"""Event study comparison plot: baseline vs. with covariates.

Creates side-by-side event study plots to show how covariate adjustment
affects treatment effect estimates and addresses pre-trend concerns.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Asymmetric display window: 12 months pre, 36 months post
PLOT_PRE_MONTHS = 12
PLOT_POST_MONTHS = 36


class EventStudyComparisonVisualizer(Visualizer):
    """Visualize event study coefficients: baseline vs. covariate-adjusted."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the event study comparison visualizer.

        Args:
            output_dir: Optional output directory for the figure.
        """
        super().__init__(
            "event_study_comparison_visualizer",
            "Event study comparison plot: baseline vs. with covariates",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create and save the event study comparison plot."""
        logger.info("Creating event study comparison plot...")

        # Get both event study results
        baseline_df = context.get("event_study_results")
        covariate_df = context.get("event_study_results_with_covariates")

        if baseline_df is None or covariate_df is None:
            logger.warning(
                "Missing event study results. Need both baseline and covariate-adjusted results."
            )
            return {}

        if baseline_df.empty or covariate_df.empty:
            logger.warning("Empty event study results. Skipping plot.")
            return {}

        # Restrict to ±3 years for display
        plot_min = -PLOT_PRE_MONTHS
        plot_max = PLOT_POST_MONTHS

        baseline_plot = baseline_df[
            (baseline_df["rel_time"] >= plot_min) & (baseline_df["rel_time"] <= plot_max)
        ].copy()

        covariate_plot = covariate_df[
            (covariate_df["rel_time"] >= plot_min) & (covariate_df["rel_time"] <= plot_max)
        ].copy()

        if baseline_plot.empty or covariate_plot.empty:
            logger.warning("No coefficients in ±%d months. Skipping plot.", PLOT_POST_MONTHS)
            return {}

        # Create side-by-side subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

        # Determine reference period
        ref_row = baseline_plot[(baseline_plot["coef"] == 0) & (baseline_plot["se"] == 0)]
        ref_period = int(ref_row["rel_time"].iloc[0]) if len(ref_row) > 0 else -1

        # Plot 1: Baseline (no covariates)
        self._plot_event_study(
            ax1, baseline_plot, ref_period, plot_min, plot_max,
            title="Baseline Event Study\n(No Covariates)"
        )

        # Plot 2: With covariates
        self._plot_event_study(
            ax2, covariate_plot, ref_period, plot_min, plot_max,
            title="Event Study with Covariate Controls\n(Adjusted for Tract Characteristics)"
        )

        # Add overall title
        covariates_used = context.get("event_study_covariates_used", [])
        if covariates_used:
            cov_str = ", ".join(covariates_used[:3])
            if len(covariates_used) > 3:
                cov_str += f", +{len(covariates_used) - 3} more"
            fig.suptitle(
                f"Event Study Comparison\nCovariates: {cov_str}",
                fontsize=14,
                y=1.00
            )

        plt.tight_layout()

        out_path = Path(self.output_dir) / "did_event_study_comparison.png"
        setup_figure_and_save(
            fig,
            out_path,
            "DiD Event Study Comparison",
            logger=logger,
        )

        logger.info("Saved event study comparison plot to %s", out_path)

        # Also create a difference plot showing the impact of covariate adjustment
        self._create_adjustment_impact_plot(
            baseline_plot, covariate_plot, ref_period, plot_min, plot_max
        )

        return {"event_study_comparison_plot_path": str(out_path)}

    def _plot_event_study(
        self,
        ax: plt.Axes,
        plot_df: pd.DataFrame,
        ref_period: int,
        plot_min: int,
        plot_max: int,
        title: str
    ) -> None:
        """Plot a single event study on the given axis."""
        # Pre-treatment and post-treatment shading
        ax.axvspan(plot_min, ref_period - 0.5, alpha=0.08, color="blue", label="Pre-treatment")
        ax.axvspan(ref_period + 0.5, plot_max, alpha=0.08, color="green", label="Post-treatment")

        # Coefficients and 95% CI
        ax.plot(
            plot_df["rel_time"],
            plot_df["coef"],
            color="black",
            marker="o",
            markersize=4,
            linewidth=1.2,
            label="Point estimate",
        )
        ax.fill_between(
            plot_df["rel_time"],
            plot_df["ci_low"],
            plot_df["ci_high"],
            alpha=0.3,
            color="gray",
            label="95% CI",
        )

        # Reference line at zero
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
        ax.axvline(ref_period, color="red", linestyle=":", linewidth=1, alpha=0.6)

        ax.set_xlabel("Months since STR prohibition", fontsize=11)
        ax.set_ylabel("Effect on rental price ($)", fontsize=11)
        ax.set_title(title, fontsize=12)
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(plot_min - 0.5, plot_max + 0.5)

    def _create_adjustment_impact_plot(
        self,
        baseline_df: pd.DataFrame,
        covariate_df: pd.DataFrame,
        ref_period: int,
        plot_min: int,
        plot_max: int
    ) -> None:
        """Create a plot showing the impact of covariate adjustment."""
        # Merge both datasets
        merged = baseline_df.merge(
            covariate_df,
            on="rel_time",
            suffixes=("_baseline", "_covariate")
        )

        # Calculate adjustment impact
        merged["adjustment"] = merged["coef_covariate"] - merged["coef_baseline"]

        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot adjustment impact
        ax.plot(
            merged["rel_time"],
            merged["adjustment"],
            color="purple",
            marker="o",
            markersize=4,
            linewidth=1.2,
            label="Covariate adjustment impact"
        )

        # Pre-treatment and post-treatment shading
        ax.axvspan(plot_min, ref_period - 0.5, alpha=0.08, color="blue", label="Pre-treatment")
        ax.axvspan(ref_period + 0.5, plot_max, alpha=0.08, color="green", label="Post-treatment")

        # Zero line
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8, label="No adjustment")
        ax.axvline(ref_period, color="red", linestyle=":", linewidth=1, alpha=0.6)

        ax.set_xlabel("Months since STR prohibition", fontsize=11)
        ax.set_ylabel("Change in coefficient ($)", fontsize=11)
        ax.set_title(
            "Impact of Covariate Adjustment on Event Study Estimates\n"
            "(Positive = covariate adjustment increases effect estimate)",
            fontsize=12
        )
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(plot_min - 0.5, plot_max + 0.5)

        plt.tight_layout()

        out_path = Path(self.output_dir) / "did_covariate_adjustment_impact.png"
        setup_figure_and_save(
            fig,
            out_path,
            "Covariate Adjustment Impact",
            logger=logger,
        )

        logger.info("Saved covariate adjustment impact plot to %s", out_path)
