"""Figures and CSV for CS post-treatment trajectory (growth vs. plateau)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from housing.components.analyzers.callaway_santanna_trajectory import (
    predicted_trajectory,
)
from housing.components.utils import setup_figure_and_save
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

PLOT_PRE_MONTHS = 12
PLOT_POST_MONTHS = 36


class CallawaySantAnnaTrajectoryVisualizer(Visualizer):
    """Plot CS event study with WLS trend overlays and phase-average bars."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Set figure/CSV output directory (default ``/project/output``)."""
        super().__init__(
            "callaway_santanna_trajectory_visualizer",
            "CS trajectory fit overlay and phase bar chart",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Write trajectory plots and ``cs_trajectory_summary.csv`` when inputs exist."""
        traj = context.get("cs_trajectory_results")
        es = context.get("cs_event_study")
        if traj is None:
            logger.warning("cs_trajectory_results missing; skip trajectory plots.")
            return {}
        if es is None or not isinstance(es, pd.DataFrame) or es.empty:
            logger.warning("cs_event_study missing; skip trajectory plots.")
            return {}

        out: dict[str, Any] = {}
        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        fit_path = self._plot_fit_overlay(es, traj, out_dir)
        if fit_path:
            out["cs_trajectory_fit_plot"] = fit_path

        phase_path = self._plot_phases(traj, out_dir)
        if phase_path:
            out["cs_trajectory_phases_plot"] = phase_path

        csv_path = self._write_summary_csv(traj, out_dir)
        if csv_path:
            out["cs_trajectory_summary_csv"] = csv_path

        return out

    def _plot_fit_overlay(
        self,
        cs_event_study: pd.DataFrame,
        traj: dict[str, Any],
        out_dir: Path,
    ) -> str | None:
        plot_df = cs_event_study[
            (cs_event_study["rel_time"] >= -PLOT_PRE_MONTHS)
            & (cs_event_study["rel_time"] <= PLOT_POST_MONTHS)
        ].copy()
        if plot_df.empty:
            return None

        fits = traj.get("fits") or {}
        classification = traj.get("classification", "")
        detail = traj.get("classification_detail", "")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axvspan(-PLOT_PRE_MONTHS, -0.5, alpha=0.08, color="blue", label="Pre-treatment")
        ax.axvspan(0.5, PLOT_POST_MONTHS, alpha=0.08, color="green", label="Post-treatment")

        ax.plot(
            plot_df["rel_time"],
            plot_df["att"],
            color="darkblue",
            marker="o",
            markersize=4,
            linewidth=1.5,
            label="CS ATT",
        )
        if "ci_low" in plot_df.columns and "ci_high" in plot_df.columns:
            ax.fill_between(
                plot_df["rel_time"],
                plot_df["ci_low"],
                plot_df["ci_high"],
                alpha=0.25,
                color="darkblue",
                label="95% CI (analytic)",
            )

        if fits and traj.get("classification") != "insufficient_data":
            grid = np.linspace(0, PLOT_POST_MONTHS, 80)
            try:
                y_lin = predicted_trajectory(grid, "linear", fits)
                y_log = predicted_trajectory(grid, "log", fits)
                ax.plot(
                    grid,
                    y_lin,
                    color="darkorange",
                    linestyle="-",
                    linewidth=2,
                    label="WLS linear (post)",
                )
                ax.plot(
                    grid,
                    y_log,
                    color="purple",
                    linestyle="--",
                    linewidth=2,
                    label="WLS log(1+e) (post)",
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.warning("Could not draw trajectory overlays: %s", e)

        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
        ax.axvline(0, color="red", linestyle=":", linewidth=1, alpha=0.6)
        ax.set_xlabel("Months since STR prohibition", fontsize=12)
        ax.set_ylabel("Average treatment effect ($)", fontsize=12)
        ax.set_title(
            "CS event study with post-treatment WLS trajectory fits\n"
            f"Classification: {classification}",
            fontsize=12,
        )
        ax.text(
            0.02,
            0.02,
            f"{detail}",
            transform=ax.transAxes,
            fontsize=8,
            verticalalignment="bottom",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.45},
        )
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-PLOT_PRE_MONTHS - 0.5, PLOT_POST_MONTHS + 0.5)

        path = out_dir / "did_cs_trajectory_fit.png"
        setup_figure_and_save(fig, path, "CS trajectory fit", logger=logger)
        return str(path)

    def _plot_phases(self, traj: dict[str, Any], out_dir: Path) -> str | None:
        phases = traj.get("phases")
        if phases is None or not isinstance(phases, pd.DataFrame) or phases.empty:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))
        x = np.arange(len(phases))
        atts = phases["att"].to_numpy(dtype=float)
        ses = phases["se"].to_numpy(dtype=float)
        ses_plot = np.where(np.isfinite(ses) & (ses > 0), ses, 0.0)
        labels = phases["phase"].astype(str).tolist()
        colors = ["#2ecc71", "#3498db", "#9b59b6"]
        bars = ax.bar(
            x,
            atts,
            yerr=1.96 * ses_plot,
            capsize=6,
            color=colors[: len(x)],
            edgecolor="black",
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.axhline(0, color="red", linestyle="--", linewidth=1)
        ax.set_ylabel("Inverse-variance mean ATT ($)", fontsize=11)
        ax.set_title(
            "Post-treatment phases (inverse-variance within window)\n"
            f"{traj.get('classification', '')}",
            fontsize=12,
        )
        ax.grid(True, axis="y", alpha=0.3)
        for i, bar in enumerate(bars):
            h = bar.get_height()
            if np.isfinite(h):
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    h + 1.96 * ses_plot[i] + 0.5,
                    f"${h:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        path = out_dir / "did_cs_trajectory_phases.png"
        setup_figure_and_save(fig, path, "CS trajectory phases", logger=logger)
        return str(path)

    def _write_summary_csv(self, traj: dict[str, Any], out_dir: Path) -> str | None:
        phases = traj.get("phases")
        if phases is None or not isinstance(phases, pd.DataFrame):
            return None

        fits = traj.get("fits") or {}
        lin = fits.get("linear") or {}
        quad = fits.get("quadratic") or {}
        log = fits.get("log") or {}
        curv = traj.get("curvature_test") or {}
        lme = traj.get("late_minus_early") or {}

        summary = {
            "row_type": "summary",
            "phase": "",
            "rel_lo": np.nan,
            "rel_hi": np.nan,
            "att": np.nan,
            "se": np.nan,
            "ci_low": np.nan,
            "ci_high": np.nan,
            "n_periods": np.nan,
            "classification": traj.get("classification", ""),
            "classification_detail": traj.get("classification_detail", ""),
            "linear_slope_e": lin.get("coefficients", {}).get("slope_e", np.nan),
            "linear_slope_p": lin.get("slope_e_p_value", np.nan),
            "quadratic_curvature": curv.get("quadratic_curvature_coef", np.nan),
            "f_quad_vs_linear": curv.get("f_statistic_quadratic_vs_linear", np.nan),
            "p_quad_vs_linear": curv.get("p_value_quadratic_vs_linear", np.nan),
            "aic_linear": lin.get("aic", np.nan),
            "aic_log": log.get("aic", np.nan),
            "aic_quadratic": quad.get("aic", np.nan),
            "late_minus_early": lme.get("estimate", np.nan),
            "late_minus_early_se": lme.get("se", np.nan),
            "late_minus_early_p": lme.get("p_value", np.nan),
        }

        p2 = phases.copy()
        p2.insert(0, "row_type", "phase")
        summary_df = pd.DataFrame([summary])
        combined = pd.concat([p2, summary_df], ignore_index=True, sort=False)

        path = out_dir / "cs_trajectory_summary.csv"
        combined.to_csv(path, index=False)
        logger.info("Wrote %s", path)
        return str(path)
