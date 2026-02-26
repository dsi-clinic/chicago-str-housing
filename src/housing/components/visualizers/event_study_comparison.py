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

        # Baseline: housing uses event_study_coefficients (relative_time, coefficient, ci_lower, ci_upper)
        baseline_df = context.get("event_study_coefficients")
        covariate_df = context.get("event_study_results_with_covariates")

        if baseline_df is None or covariate_df is None:
            logger.warning(
                "Missing event study results. Need both baseline and covariate-adjusted results."
            )
            return {}

        if baseline_df.empty or covariate_df.empty:
            logger.warning("Empty event study results. Skipping plot.")
            return {}

        plot_min = -PLOT_PRE_MONTHS
        plot_max = PLOT_POST_MONTHS

        # Baseline: housing format uses relative_time
        time_col_baseline = "relative_time" if "relative_time" in baseline_df.columns else "rel_time"
        baseline_plot = baseline_df[
            (baseline_df[time_col_baseline] >= plot_min) & (baseline_df[time_col_baseline] <= plot_max)
        ].copy()

        covariate_plot = covariate_df[
            (covariate_df["rel_time"] >= plot_min) & (covariate_df["rel_time"] <= plot_max)
        ].copy()

        if baseline_plot.empty or covariate_plot.empty:
            logger.warning("No coefficients in ±%d months. Skipping plot.", PLOT_POST_MONTHS)
            return {}

        # Reference period: baseline has coefficient=0 (housing) or coef=0 (housing-2)
        coef_col_baseline = "coefficient" if "coefficient" in baseline_plot.columns else "coef"
        ref_row = baseline_plot[(baseline_plot[coef_col_baseline] == 0)]
        ref_period = int(ref_row[time_col_baseline].iloc[0]) if len(ref_row) > 0 else -1

        fig, (ax1, ax2) = plt.subplots(
            1, 2, figsize=(16, 6), sharey=True, sharex=True
        )

        # Plot 1: Baseline (housing column names: relative_time, coefficient, ci_lower, ci_upper)
        self._plot_event_study(
            ax1, baseline_plot, ref_period, plot_min, plot_max,
            title="Baseline Event Study\n(No Covariates)",
            time_col=time_col_baseline,
            coef_col=coef_col_baseline,
            ci_low_col="ci_lower" if "ci_lower" in baseline_plot.columns else "ci_low",
            ci_high_col="ci_upper" if "ci_upper" in baseline_plot.columns else "ci_high",
        )

        # Plot 2: With covariates (rel_time, coef, ci_low, ci_high)
        self._plot_event_study(
            ax2, covariate_plot, ref_period, plot_min, plot_max,
            title="Event Study with Covariate Controls\n(Adjusted for Tract Characteristics)"
        )

        # Force both panels to the same x range (12m before, 36m after)
        ax1.set_xlim(plot_min - 0.5, plot_max + 0.5)
        ax2.set_xlim(plot_min - 0.5, plot_max + 0.5)

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

        # Impact plot: need common columns for merge; use rel_time and coef for both
        baseline_for_merge = baseline_plot.copy()
        if "relative_time" in baseline_for_merge.columns:
            baseline_for_merge["rel_time"] = baseline_for_merge["relative_time"]
        if "coefficient" in baseline_for_merge.columns:
            baseline_for_merge["coef"] = baseline_for_merge["coefficient"]
        self._create_adjustment_impact_plot(
            baseline_for_merge, covariate_plot, ref_period, plot_min, plot_max
        )

        return {"event_study_comparison_plot_path": str(out_path)}

    def _plot_event_study(
        self,
        ax: plt.Axes,
        plot_df: pd.DataFrame,
        ref_period: int,
        plot_min: int,
        plot_max: int,
        title: str,
        *,
        time_col: str = "rel_time",
        coef_col: str = "coef",
        ci_low_col: str = "ci_low",
        ci_high_col: str = "ci_high",
    ) -> None:
        """Plot a single event study on the given axis."""
        ax.axvspan(plot_min, ref_period - 0.5, alpha=0.08, color="blue", label="Pre-treatment")
        ax.axvspan(ref_period + 0.5, plot_max, alpha=0.08, color="green", label="Post-treatment")

        ax.plot(
            plot_df[time_col],
            plot_df[coef_col],
            color="black",
            marker="o",
            markersize=4,
            linewidth=1.2,
            label="Point estimate",
        )
        ax.fill_between(
            plot_df[time_col],
            plot_df[ci_low_col],
            plot_df[ci_high_col],
            alpha=0.3,
            color="gray",
            label="95% CI",
        )

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
        merged = baseline_df.merge(
            covariate_df,
            on="rel_time",
            suffixes=("_baseline", "_covariate")
        )

        merged["adjustment"] = merged["coef_covariate"] - merged["coef_baseline"]

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(
            merged["rel_time"],
            merged["adjustment"],
            color="purple",
            marker="o",
            markersize=4,
            linewidth=1.2,
            label="Covariate adjustment impact"
        )

        ax.axvspan(plot_min, ref_period - 0.5, alpha=0.08, color="blue", label="Pre-treatment")
        ax.axvspan(ref_period + 0.5, plot_max, alpha=0.08, color="green", label="Post-treatment")

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
