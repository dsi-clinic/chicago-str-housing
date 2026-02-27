"""Visualizations for Callaway & Sant'Anna (2021) estimator results.

Creates event study plots and comparison with TWFE estimates to highlight
differences when treatment effects are heterogeneous.
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


def _get_twfe_results_df(context: dict[str, Any]) -> pd.DataFrame | None:
    """Return TWFE event study as DataFrame with rel_time, coef, ci_low, ci_high, se.

    Housing's EventStudyAnalyzer stores raw PanelOLS in event_study_results and
    the coefficient table in event_study_coefficients (relative_time, coefficient,
    ci_lower, ci_upper, std_error). Normalize to the format expected by CS
    comparison plots and table.
    """
    event_study_results = context.get("event_study_results")
    if isinstance(event_study_results, pd.DataFrame) and not event_study_results.empty:
        return event_study_results
    coef_df = context.get("event_study_coefficients")
    if coef_df is None or coef_df.empty:
        return None
    # Map housing column names to TWFE comparison format; drop k=-1 reference period
    twfe_data = coef_df.rename(
        columns={
            "relative_time": "rel_time",
            "coefficient": "coef",
            "ci_lower": "ci_low",
            "ci_upper": "ci_high",
            "std_error": "se",
        }
    )[["rel_time", "coef", "ci_low", "ci_high", "se"]].copy()
    return twfe_data[twfe_data["rel_time"] != -1].reset_index(drop=True)


class CallawaySantAnnaVisualizer(Visualizer):
    """Visualize Callaway & Sant'Anna event study results."""

    def __init__(
        self,
        output_dir: str | None = None,
        context_suffix: str = "",
        output_suffix: str = "",
    ) -> None:
        """Initialize the visualizer.

        Args:
            output_dir: Optional output directory for figures.
            context_suffix: Optional suffix for context keys (e.g. "_with_controls" to read
                cs_event_study_with_controls, cs_overall_att_with_controls).
            output_suffix: Optional suffix for output filenames (e.g. "_with_controls").
        """
        super().__init__(
            "callaway_santanna_visualizer",
            "Callaway & Sant'Anna event study visualization",
        )
        self.output_dir = output_dir or "/project/output"
        self.context_suffix = context_suffix
        self.output_suffix = output_suffix

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create Callaway & Sant'Anna visualizations."""
        logger.info("Creating Callaway & Sant'Anna visualizations...")

        cs_event_study = context.get(f"cs_event_study{self.context_suffix}")
        if cs_event_study is None or cs_event_study.empty:
            logger.warning(
                "cs_event_study%s not found or empty. Skipping visualization.",
                self.context_suffix,
            )
            return {}

        output_paths = {}

        # 1. Main event study plot
        event_study_path = self._plot_event_study(cs_event_study, context)
        if event_study_path:
            output_paths["cs_event_study_plot"] = event_study_path

        # 2. Comparison with TWFE (only for base CS, not for with_controls)
        if not self.context_suffix:
            comparison_path = self._plot_twfe_comparison(cs_event_study, context)
            if comparison_path:
                output_paths["cs_twfe_comparison_plot"] = comparison_path

        # 3. Cohort-specific dynamics (only for base CS, not for with_controls)
        if not self.context_suffix:
            cohort_path = self._plot_cohort_dynamics(context)
            if cohort_path:
                output_paths["cs_cohort_dynamics_plot"] = cohort_path

        return output_paths

    def _plot_event_study(
        self, cs_event_study: pd.DataFrame, context: dict[str, Any]
    ) -> str | None:
        """Create main Callaway & Sant'Anna event study plot."""
        # Restrict to display window
        plot_df = cs_event_study[
            (cs_event_study["rel_time"] >= -PLOT_PRE_MONTHS)
            & (cs_event_study["rel_time"] <= PLOT_POST_MONTHS)
        ].copy()

        if plot_df.empty:
            logger.warning("No CS estimates in ±%d months window", PLOT_POST_MONTHS)
            return None

        fig, ax = plt.subplots(figsize=(10, 6))

        # Pre-treatment and post-treatment shading
        ax.axvspan(
            -PLOT_PRE_MONTHS, -0.5, alpha=0.08, color="blue", label="Pre-treatment"
        )
        ax.axvspan(
            0.5, PLOT_POST_MONTHS, alpha=0.08, color="green", label="Post-treatment"
        )

        # Plot ATT estimates with confidence intervals
        ax.plot(
            plot_df["rel_time"],
            plot_df["att"],
            color="darkblue",
            marker="o",
            markersize=4,
            linewidth=1.5,
            label="Callaway-Sant'Anna ATT",
        )
        ax.fill_between(
            plot_df["rel_time"],
            plot_df["ci_low"],
            plot_df["ci_high"],
            alpha=0.3,
            color="darkblue",
            label="95% CI",
        )

        # Reference lines
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
        ax.axvline(
            0,
            color="red",
            linestyle=":",
            linewidth=1,
            alpha=0.6,
            label="Treatment begins",
        )

        # Get overall ATT for annotation
        overall_att = context.get(f"cs_overall_att{self.context_suffix}", {})
        if overall_att and "att" in overall_att:
            att_val = overall_att["att"]
            se_val = overall_att.get("se", 0)
            ax.text(
                0.02,
                0.98,
                f"Overall ATT: ${att_val:.2f}\n(SE: ${se_val:.2f})",
                transform=ax.transAxes,
                verticalalignment="top",
                bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
                fontsize=9,
            )

        ax.set_xlabel("Months since STR prohibition", fontsize=12)
        ax.set_ylabel("Average Treatment Effect on Rental Price ($)", fontsize=12)
        title_suffix = " (with controls)" if self.output_suffix else ""
        ax.set_title(
            "Event Study: Callaway & Sant'Anna (2021) Estimator\n"
            f"Robust to Heterogeneous Treatment Effects{title_suffix}",
            fontsize=13,
        )
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-PLOT_PRE_MONTHS - 0.5, PLOT_POST_MONTHS + 0.5)

        out_path = (
            Path(self.output_dir)
            / f"did_callaway_santanna_event_study{self.output_suffix}.png"
        )
        setup_figure_and_save(fig, out_path, "CS Event Study", logger=logger)

        logger.info("Saved Callaway-Sant'Anna event study to %s", out_path)
        return str(out_path)

    def _plot_twfe_comparison(
        self, cs_event_study: pd.DataFrame, context: dict[str, Any]
    ) -> str | None:
        """Create side-by-side comparison of TWFE vs. Callaway-Sant'Anna."""
        # Get TWFE results (support housing's event_study_coefficients format)
        twfe_results = _get_twfe_results_df(context)
        if twfe_results is None or twfe_results.empty:
            logger.warning("No TWFE results for comparison. Skipping comparison plot.")
            return None

        # Restrict both to display window
        cs_plot = cs_event_study[
            (cs_event_study["rel_time"] >= -PLOT_PRE_MONTHS)
            & (cs_event_study["rel_time"] <= PLOT_POST_MONTHS)
        ].copy()

        twfe_plot = twfe_results[
            (twfe_results["rel_time"] >= -PLOT_PRE_MONTHS)
            & (twfe_results["rel_time"] <= PLOT_POST_MONTHS)
        ].copy()

        if cs_plot.empty or twfe_plot.empty:
            logger.warning("Empty data for comparison plot")
            return None

        # Create side-by-side plots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), sharey=True)

        # TWFE plot (left)
        self._plot_single_event_study(
            ax1,
            twfe_plot,
            "TWFE Event Study\n(May have negative weight bias)",
            color="black",
            coef_col="coef",
            ci_low_col="ci_low",
            ci_high_col="ci_high",
        )

        # CS plot (right)
        self._plot_single_event_study(
            ax2,
            cs_plot,
            "Callaway-Sant'Anna Event Study\n(Robust to heterogeneity)",
            color="darkblue",
            coef_col="att",
            ci_low_col="ci_low",
            ci_high_col="ci_high",
        )

        # Overall title
        fig.suptitle(
            "Comparison: TWFE vs. Callaway-Sant'Anna (2021)\n"
            "Differences indicate heterogeneous treatment effects",
            fontsize=14,
            y=1.00,
        )

        plt.tight_layout()

        out_path = Path(self.output_dir) / "did_twfe_vs_cs_comparison.png"
        setup_figure_and_save(fig, out_path, "TWFE vs CS Comparison", logger=logger)

        logger.info("Saved TWFE vs. CS comparison to %s", out_path)

        # Also create a difference plot
        self._plot_difference(cs_plot, twfe_plot)

        return str(out_path)

    def _plot_single_event_study(
        self,
        ax: plt.Axes,
        data: pd.DataFrame,
        title: str,
        color: str,
        coef_col: str,
        ci_low_col: str,
        ci_high_col: str,
    ) -> None:
        """Plot a single event study on given axis."""
        # Shading
        ax.axvspan(
            -PLOT_PRE_MONTHS, -0.5, alpha=0.08, color="blue", label="Pre-treatment"
        )
        ax.axvspan(
            0.5, PLOT_POST_MONTHS, alpha=0.08, color="green", label="Post-treatment"
        )

        # Plot estimates
        ax.plot(
            data["rel_time"],
            data[coef_col],
            color=color,
            marker="o",
            markersize=4,
            linewidth=1.5,
            label="Point estimate",
        )
        ax.fill_between(
            data["rel_time"],
            data[ci_low_col],
            data[ci_high_col],
            alpha=0.3,
            color=color,
            label="95% CI",
        )

        # Reference lines
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
        ax.axvline(0, color="red", linestyle=":", linewidth=1, alpha=0.6)

        ax.set_xlabel("Months since STR prohibition", fontsize=11)
        ax.set_ylabel("Effect on rental price ($)", fontsize=11)
        ax.set_title(title, fontsize=12)
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-PLOT_PRE_MONTHS - 0.5, PLOT_POST_MONTHS + 0.5)

    def _plot_difference(self, cs_plot: pd.DataFrame, twfe_plot: pd.DataFrame) -> None:
        """Plot difference between CS and TWFE estimates."""
        # Merge on relative time
        merged = cs_plot.merge(
            twfe_plot[["rel_time", "coef"]],
            on="rel_time",
            suffixes=("_cs", "_twfe"),
        )

        merged["difference"] = merged["att"] - merged["coef"]

        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot difference
        ax.plot(
            merged["rel_time"],
            merged["difference"],
            color="purple",
            marker="o",
            markersize=4,
            linewidth=1.5,
            label="CS - TWFE",
        )

        # Shading
        ax.axvspan(
            -PLOT_PRE_MONTHS, -0.5, alpha=0.08, color="blue", label="Pre-treatment"
        )
        ax.axvspan(
            0.5, PLOT_POST_MONTHS, alpha=0.08, color="green", label="Post-treatment"
        )

        # Zero line
        ax.axhline(
            0,
            color="red",
            linestyle="--",
            linewidth=1,
            alpha=0.8,
            label="No difference",
        )
        ax.axvline(0, color="red", linestyle=":", linewidth=1, alpha=0.6)

        ax.set_xlabel("Months since STR prohibition", fontsize=11)
        ax.set_ylabel("Difference in estimates (CS - TWFE) ($)", fontsize=11)
        ax.set_title(
            "Difference: Callaway-Sant'Anna vs. TWFE\n"
            "(Non-zero values indicate TWFE bias from heterogeneity)",
            fontsize=12,
        )
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-PLOT_PRE_MONTHS - 0.5, PLOT_POST_MONTHS + 0.5)

        plt.tight_layout()

        out_path = Path(self.output_dir) / "did_cs_twfe_difference.png"
        setup_figure_and_save(fig, out_path, "CS-TWFE Difference", logger=logger)

        logger.info("Saved difference plot to %s", out_path)

    def _plot_cohort_dynamics(self, context: dict[str, Any]) -> str | None:
        """Plot dynamic effects for each treatment cohort separately."""
        cohort_dynamics = context.get(f"cs_cohort_dynamics{self.context_suffix}")
        if cohort_dynamics is None or cohort_dynamics.empty:
            logger.warning("No cohort dynamics data. Skipping cohort plot.")
            return None

        # Restrict to display window
        plot_df = cohort_dynamics[
            (cohort_dynamics["rel_time"] >= -PLOT_PRE_MONTHS)
            & (cohort_dynamics["rel_time"] <= PLOT_POST_MONTHS)
        ].copy()

        if plot_df.empty:
            return None

        cohorts = sorted(plot_df["cohort"].unique())
        n_cohorts = len(cohorts)

        if n_cohorts == 0:
            return None

        # Create subplots (max 4 per row)
        n_cols = min(2, n_cohorts)
        n_rows = (n_cohorts + n_cols - 1) // n_cols

        fig, axes = plt.subplots(
            n_rows, n_cols, figsize=(8 * n_cols, 5 * n_rows), squeeze=False
        )
        axes = axes.flatten()

        for idx, cohort in enumerate(cohorts):
            ax = axes[idx]
            cohort_data = plot_df[plot_df["cohort"] == cohort].sort_values("rel_time")

            # Plot
            ax.plot(
                cohort_data["rel_time"],
                cohort_data["att"],
                color="darkgreen",
                marker="o",
                markersize=3,
                linewidth=1.2,
            )
            ax.fill_between(
                cohort_data["rel_time"],
                cohort_data["ci_low"],
                cohort_data["ci_high"],
                alpha=0.3,
                color="darkgreen",
            )

            # Reference lines
            ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
            ax.axvline(0, color="red", linestyle=":", linewidth=1, alpha=0.6)

            ax.set_xlabel("Months since treatment", fontsize=10)
            ax.set_ylabel("ATT ($)", fontsize=10)
            ax.set_title(f"Cohort: {str(cohort)[:7]}", fontsize=11)
            ax.grid(True, alpha=0.3)

        # Hide extra subplots
        for idx in range(n_cohorts, len(axes)):
            axes[idx].axis("off")

        fig.suptitle(
            "Cohort-Specific Dynamic Treatment Effects\n"
            "Each panel shows effects for one treatment cohort",
            fontsize=14,
        )
        plt.tight_layout()

        out_path = Path(self.output_dir) / "did_cohort_dynamics.png"
        setup_figure_and_save(fig, out_path, "Cohort Dynamics", logger=logger)

        logger.info("Saved cohort dynamics plot to %s", out_path)
        return str(out_path)


class CallawaySantAnnaComparisonVisualizer(Visualizer):
    """Create comprehensive comparison of TWFE vs. CS estimates."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the comparison visualizer.

        Args:
            output_dir: Optional output directory for figures.
        """
        super().__init__(
            "cs_comparison_visualizer",
            "TWFE vs. Callaway-Sant'Anna comprehensive comparison",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create comprehensive comparison visualizations."""
        logger.info("Creating TWFE vs. CS comprehensive comparison...")

        # Get both estimates (support housing's event_study_coefficients format)
        cs_event_study = context.get("cs_event_study")
        twfe_results = _get_twfe_results_df(context)
        cs_overall = context.get("cs_overall_att", {})

        if cs_event_study is None or twfe_results is None:
            logger.warning("Missing data for comparison. Skipping.")
            return {}

        # Create comparison table
        comparison_table = self._create_comparison_table(
            cs_event_study, twfe_results, cs_overall, context
        )

        # Save comparison table
        table_path = Path(self.output_dir) / "did_twfe_cs_comparison_table.csv"
        comparison_table.to_csv(table_path, index=False)
        logger.info("Saved comparison table to %s", table_path)

        return {
            "comparison_table_path": str(table_path),
            "comparison_table": comparison_table,
        }

    def _create_comparison_table(
        self,
        cs_results: pd.DataFrame,
        twfe_results: pd.DataFrame,
        cs_overall: dict,
        context: dict[str, Any],
    ) -> pd.DataFrame:
        """Create comparison table of key estimates."""
        # Merge on relative time
        merged = cs_results.merge(
            twfe_results[["rel_time", "coef", "se"]],
            on="rel_time",
            suffixes=("_cs", "_twfe"),
        )

        # Calculate differences
        merged["diff_point_estimate"] = merged["att"] - merged["coef"]
        merged["diff_se"] = merged["se_cs"] - merged["se_twfe"]

        # Rename columns for clarity
        merged = merged.rename(
            columns={
                "att": "CS_ATT",
                "se_cs": "CS_SE",
                "coef": "TWFE_Coef",
                "se_twfe": "TWFE_SE",
            }
        )

        return merged[
            [
                "rel_time",
                "CS_ATT",
                "CS_SE",
                "TWFE_Coef",
                "TWFE_SE",
                "diff_point_estimate",
                "diff_se",
            ]
        ]
