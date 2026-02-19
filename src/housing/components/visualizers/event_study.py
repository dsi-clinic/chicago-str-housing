"""Event study plot for Difference-in-Differences.

Produces the canonical event study figure: coefficient by months since treatment
with 95% confidence intervals and reference period at zero. X-axis limited to
12 months pre / 36 months post to match data availability for the largest cohorts.
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


class EventStudyVisualizer(Visualizer):
    """Visualize event study coefficients and confidence intervals."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the event study visualizer.

        Args:
            output_dir: Optional output directory for the figure.
        """
        super().__init__(
            "event_study_visualizer",
            "Event study plot: treatment effects by months since treatment",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create and save the event study plot."""
        logger.info("Creating event study plot...")

        event_df = context.get("event_study_results")
        if event_df is None or not isinstance(event_df, pd.DataFrame):
            logger.warning(
                "event_study_results not found in context. Run EventStudyAnalyzer first."
            )
            return {}

        if event_df.empty:
            logger.warning("event_study_results is empty. Skipping plot.")
            return {}

        # Restrict to ±3 years for display (hide far lead/lag bins -999 and 999)
        plot_min = -PLOT_PRE_MONTHS
        plot_max = PLOT_POST_MONTHS
        plot_df = event_df[
            (event_df["rel_time"] >= plot_min) & (event_df["rel_time"] <= plot_max)
        ].copy()
        if plot_df.empty:
            logger.warning("No event study coefficients in ±%d months. Skipping plot.", PLOT_POST_MONTHS)
            return {}

        fig, ax = plt.subplots(figsize=(10, 6))

        # Reference period is the row we set to (coef=0, se=0)
        ref_row = plot_df[(plot_df["coef"] == 0) & (plot_df["se"] == 0)]
        ref_period = int(ref_row["rel_time"].iloc[0]) if len(ref_row) > 0 else -1

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

        # Reference line at zero (reference period)
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
        ax.axvline(ref_period, color="red", linestyle=":", linewidth=1, alpha=0.6)

        ax.set_xlabel("Months since STR prohibition", fontsize=12)
        ax.set_ylabel("Effect on rental price ($)", fontsize=12)
        ax.set_title("Event Study: Effect of STR Prohibition on Tract-Level Rental Prices\n(12 months pre / 36 months post)", fontsize=13)
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(plot_min - 0.5, plot_max + 0.5)

        out_path = Path(self.output_dir) / "did_event_study.png"
        setup_figure_and_save(
            fig,
            out_path,
            "DiD Event Study",
            logger=logger,
        )

        logger.info("Saved event study plot to %s", out_path)
        return {"event_study_plot_path": str(out_path)}
