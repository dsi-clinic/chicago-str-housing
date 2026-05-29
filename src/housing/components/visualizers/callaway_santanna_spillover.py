"""Figures and tables for Callaway–Sant'Anna spillover analysis."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

PLOT_PRE_MONTHS = 12
PLOT_POST_MONTHS = 36


class CallawaySantAnnaSpilloverVisualizer(Visualizer):
    """Event study plot and CSV exports for spillover CS."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize visualizer with optional output directory."""
        super().__init__(
            "callaway_santanna_spillover_visualizer",
            "Callaway & Sant'Anna spillover plots and tables",
        )
        self.output_dir = output_dir or "/project/output/did-cs"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write spillover summary, classification CSV, and event-study figure."""
        res = context.get("cs_spillover_results")
        if not res:
            logger.warning("cs_spillover_results missing; skip spillover visualizer.")
            return {}

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        out_paths: dict[str, str] = {}

        meta = res.get("meta") or {}
        core = res.get("core") or {}
        oa = core.get("overall_att") or {}
        classification = res.get("classification")
        if not isinstance(classification, pd.DataFrame):
            classification = pd.DataFrame()

        summary_row = {
            "att": float(oa.get("att", float("nan"))),
            "se": float(oa.get("se", float("nan"))),
            "ci_low": float(oa.get("ci_low", float("nan"))),
            "ci_high": float(oa.get("ci_high", float("nan"))),
            "p_value": float(oa.get("p_value", float("nan"))),
            "n_treated_original": int(meta.get("n_treated", 0) or 0),
            "n_spillover": int(meta.get("n_spillover", 0) or 0),
            "n_pure_control": int(meta.get("n_pure_control", 0) or 0),
            "n_never_missing_geometry": int(
                meta.get("n_never_missing_geometry", 0) or 0
            ),
            "comparison_group": str(meta.get("comparison_group", "")),
            "min_cohort_size": int(meta.get("min_cohort_size", 0) or 0),
        }
        summary_df = pd.DataFrame([summary_row])
        p_summary = Path(self.output_dir) / "cs_spillover_summary.csv"
        summary_df.to_csv(p_summary, index=False)
        out_paths["cs_spillover_summary_csv"] = str(p_summary)
        logger.info("Wrote %s", p_summary)

        p_class = Path(self.output_dir) / "cs_spillover_classification.csv"
        classification.to_csv(p_class, index=False)
        out_paths["cs_spillover_classification_csv"] = str(p_class)
        logger.info("Wrote %s (%d rows)", p_class, len(classification))

        es = core.get("event_study")
        if isinstance(es, pd.DataFrame) and not es.empty:
            plot_path = self._plot_event_study(es, oa, meta)
            if plot_path:
                out_paths["cs_spillover_event_study_plot"] = plot_path
        else:
            logger.warning("No spillover event-study data; skip plot.")

        return out_paths

    def _plot_event_study(
        self,
        event_study: pd.DataFrame,
        overall_att: dict[str, Any],
        meta: dict[str, Any],
    ) -> str | None:
        plot_df = event_study[
            (event_study["rel_time"] >= -PLOT_PRE_MONTHS)
            & (event_study["rel_time"] <= PLOT_POST_MONTHS)
        ].copy()
        if plot_df.empty:
            return None

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axvspan(-PLOT_PRE_MONTHS, -0.5, alpha=0.08, color="blue")
        ax.axvspan(0.5, PLOT_POST_MONTHS, alpha=0.08, color="green")
        ax.plot(
            plot_df["rel_time"],
            plot_df["att"],
            color="darkgreen",
            marker="o",
            markersize=4,
            linewidth=1.5,
            label="Spillover ATT (adjacent never-treated)",
        )
        lo = (
            plot_df["ci_low"]
            if "ci_low" in plot_df.columns
            else plot_df["att"] - 1.96 * plot_df["se"]
        )
        hi = (
            plot_df["ci_high"]
            if "ci_high" in plot_df.columns
            else plot_df["att"] + 1.96 * plot_df["se"]
        )
        ax.fill_between(plot_df["rel_time"], lo, hi, alpha=0.25, color="darkgreen")
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
        ax.axvline(0, color="red", linestyle=":", linewidth=1, alpha=0.6)

        att_val = overall_att.get("att", float("nan"))
        se_val = overall_att.get("se", float("nan"))
        n_sp = meta.get("n_spillover", "n/a")
        n_pc = meta.get("n_pure_control", "n/a")
        ax.text(
            0.02,
            0.98,
            f"Overall ATT: ${float(att_val):.2f}\n(SE: ${float(se_val):.2f})\n"
            f"Spillover tracts: {n_sp}, Pure controls: {n_pc}",
            transform=ax.transAxes,
            verticalalignment="top",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
            fontsize=9,
        )

        ax.set_xlabel(
            "Months since inherited neighbor prohibition (spillover cohort)",
            fontsize=11,
        )
        ax.set_ylabel("ATT on rental price ($)", fontsize=11)
        ax.set_title(
            "Spillover test: never-treated adjacent to prohibited tracts\n"
            "vs. never-treated with no treated neighbor (Callaway–Sant'Anna)",
            fontsize=12,
            pad=12,
        )
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-PLOT_PRE_MONTHS - 0.5, PLOT_POST_MONTHS + 0.5)

        out_path = Path(self.output_dir) / "did_cs_spillover_event_study.png"
        setup_figure_and_save(fig, out_path, title=None, logger=logger)
        logger.info("Saved %s", out_path)
        return str(out_path)
