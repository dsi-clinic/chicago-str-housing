"""Event Study Visualization.

This module creates event study plots showing treatment effects
over time relative to the treatment date.
"""

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

# Event window for all event study plots: 12 months before, 36 months after
EVENT_STUDY_PRE_MONTHS = 12
EVENT_STUDY_POST_MONTHS = 36


class EventStudyVisualizer(Visualizer):
    """Create event study visualization.

    This visualizer creates:
    1. Event study plot with coefficients and confidence intervals
    2. Clear marking of pre/post treatment periods
    3. Reference line at zero and treatment timing
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the event study visualizer.

        Args:
            output_dir: Optional output directory for visualizations
        """
        super().__init__(
            "event_study_visualization",
            "Create event study plot showing dynamic treatment effects",
        )
        self.output_dir = Path(output_dir or "/project/output")
        self.required_data = ["event_study_coefficients", "parallel_trends_test"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create event study visualization.

        Required context keys:
            - event_study_coefficients: DataFrame with coefficients and CIs
            - parallel_trends_test: Results of parallel trends test

        Returns:
            Dictionary with path to saved visualization
        """
        logger.info("Creating event study visualization...")

        coef_df = context["event_study_coefficients"]
        parallel_trends_test = context["parallel_trends_test"]

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create the event study plot
        plot_path = self._create_event_study_plot(coef_df, parallel_trends_test)

        logger.info("Event study visualization saved to: %s", self.output_dir)

        return {"event_study_plot": str(plot_path)}

    def _create_event_study_plot(
        self, coef_df: pd.DataFrame, parallel_trends_test: dict[str, Any]
    ) -> Path:
        """Create the main event study plot."""
        fig, ax = plt.subplots(figsize=(12, 6))

        # Drop k=-1 reference period (normalized to 0) and sort
        coef_df = coef_df[coef_df["relative_time"] != -1].sort_values("relative_time")

        # Plot coefficients as points with lines
        ax.plot(
            coef_df["relative_time"],
            coef_df["coefficient"],
            "o-",
            color="#2c3e50",
            markersize=6,
            linewidth=1.5,
            label="Point Estimate",
        )

        # Plot confidence intervals as shaded region
        ax.fill_between(
            coef_df["relative_time"],
            coef_df["ci_lower"],
            coef_df["ci_upper"],
            alpha=0.2,
            color="#3498db",
            label="95% CI",
        )

        # Reference line at zero
        ax.axhline(0, color="black", linestyle="-", linewidth=0.8, alpha=0.7)

        # Vertical line at treatment (between -1 and 0)
        ax.axvline(
            -0.5,
            color="#e74c3c",
            linestyle="--",
            linewidth=2,
            label="Treatment",
        )

        # Shade pre-treatment period
        ax.axvspan(
            coef_df["relative_time"].min() - 0.5,
            -0.5,
            alpha=0.05,
            color="gray",
        )

        # Labels and title
        ax.set_xlabel("Months Relative to Treatment", fontsize=12)
        ax.set_ylabel("Effect on Monthly Rent ($)", fontsize=12)
        ax.set_title(
            "Event Study: Dynamic Effects of STR Prohibition on Rents",
            fontsize=14,
            fontweight="bold",
        )

        # Add annotation about parallel trends
        conclusion = parallel_trends_test.get("conclusion", "")
        if "violation" in conclusion.lower():
            trend_color = "#e74c3c"  # Red for violation
        else:
            trend_color = "#27ae60"  # Green for plausible

        ax.annotate(
            f"Pre-trends: {parallel_trends_test.get('n_significant', 0)}/{parallel_trends_test.get('n_pre_periods', 0)} significant",
            xy=(0.02, 0.98),
            xycoords="axes fraction",
            fontsize=10,
            verticalalignment="top",
            bbox={"boxstyle": "round", "facecolor": trend_color, "alpha": 0.1},
        )

        # Grid
        ax.grid(True, alpha=0.3)

        # Legend
        ax.legend(loc="upper right")

        # Fixed event window: -12 to +36 months (same across all event studies)
        ax.set_xlim(
            -EVENT_STUDY_PRE_MONTHS - 0.5,
            EVENT_STUDY_POST_MONTHS + 0.5,
        )
        ax.set_xticks(
            range(
                -EVENT_STUDY_PRE_MONTHS,
                EVENT_STUDY_POST_MONTHS + 1,
                4,
            )
        )

        plt.tight_layout()

        # Save
        output_path = self.output_dir / "event_study_plot.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info("  Saved event study plot: %s", output_path)

        return output_path


class EventStudyCovariatesVisualizer(Visualizer):
    """Create event study plot for the covariate-adjusted specification only.

    Reads event_study_results_with_covariates (rel_time, coef, ci_low, ci_high)
    and saves a single-panel plot to output_dir/event_study_with_covariates.png.
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the visualizer with optional output directory."""
        super().__init__(
            "event_study_covariates_visualization",
            "Event study plot (with covariate controls)",
        )
        self.output_dir = Path(output_dir or "/project/output")
        self.required_data = ["event_study_results_with_covariates"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create event study plot from covariate-adjusted results and save to output_dir."""
        logger.info("Creating event study visualization (with covariates)...")

        coef_df = context["event_study_results_with_covariates"].copy()
        coef_df = coef_df.sort_values("rel_time")

        plot_min = -EVENT_STUDY_PRE_MONTHS
        plot_max = EVENT_STUDY_POST_MONTHS
        ref_period = -1

        plot_df = coef_df[
            (coef_df["rel_time"] >= plot_min) & (coef_df["rel_time"] <= plot_max)
        ]
        if plot_df.empty:
            logger.warning(
                "No coefficients in [%d, %d]. Skipping plot.", plot_min, plot_max
            )
            return {}

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Constant 95% band: ±1.96 * mean(SE) across bins with valid SE
        se_vals = plot_df["se"].dropna()
        se_vals = se_vals[se_vals > 0]
        if len(se_vals) > 0:
            mean_se = float(se_vals.mean())
            half_width = 1.96 * mean_se
            ci_low = plot_df["coef"] - half_width
            ci_high = plot_df["coef"] + half_width
        else:
            ci_low = ci_high = None

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axvspan(
            plot_min, ref_period - 0.5, alpha=0.08, color="blue", label="Pre-treatment"
        )
        ax.axvspan(
            ref_period + 0.5,
            plot_max,
            alpha=0.08,
            color="green",
            label="Post-treatment",
        )
        ax.plot(
            plot_df["rel_time"],
            plot_df["coef"],
            color="black",
            marker="o",
            markersize=4,
            linewidth=1.2,
            label="Point estimate",
        )
        if ci_low is not None:
            ax.fill_between(
                plot_df["rel_time"],
                ci_low,
                ci_high,
                alpha=0.3,
                color="gray",
                label="95% CI (±1.96 × mean SE)",
            )
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
        ax.axvline(ref_period, color="red", linestyle=":", linewidth=1, alpha=0.6)
        ax.set_xlabel("Months since STR prohibition", fontsize=11)
        ax.set_ylabel("Effect on rental price ($)", fontsize=11)
        ax.set_title("Event Study with Covariate Controls", fontsize=12)
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(plot_min - 0.5, plot_max + 0.5)
        ax.set_xticks(range(plot_min, plot_max + 1, 4))

        plt.tight_layout()
        out_path = self.output_dir / "event_study_with_covariates.png"
        setup_figure_and_save(
            fig,
            out_path,
            "Event Study with Covariates",
            logger=logger,
        )
        plt.close()

        logger.info("Saved event study (covariates) plot: %s", out_path)
        return {"event_study_with_covariates_plot": str(out_path)}
