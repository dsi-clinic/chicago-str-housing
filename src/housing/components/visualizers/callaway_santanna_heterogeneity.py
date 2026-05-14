"""Figures and tables for Callaway–Sant'Anna subgroup heterogeneity."""

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


def _fmt_num(x: object, fmt: str, *, suffix: str = "") -> str:
    if x is None:
        return "n/a"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return "n/a"
    if xf != xf:  # NaN
        return "n/a"
    return f"{xf:{fmt}}{suffix}"


def _window(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df[
        (df["rel_time"] >= -PLOT_PRE_MONTHS) & (df["rel_time"] <= PLOT_POST_MONTHS)
    ].copy()


def _plot_overlay_event_study(
    ax: plt.Axes,
    series: list[tuple[str, pd.DataFrame, str]],
    title: str,
    ylabel: str,
) -> None:
    ax.axvspan(-PLOT_PRE_MONTHS, -0.5, alpha=0.08, color="blue")
    ax.axvspan(0.5, PLOT_POST_MONTHS, alpha=0.08, color="green")
    ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.8)
    ax.axvline(0, color="red", linestyle=":", linewidth=1, alpha=0.6)

    for label, df, color in series:
        w = _window(df)
        if w.empty:
            continue
        w = w.sort_values("rel_time")
        ax.plot(
            w["rel_time"],
            w["att"],
            color=color,
            marker="o",
            markersize=4,
            linewidth=1.5,
            label=label,
        )
        lo = w["ci_low"] if "ci_low" in w.columns else w["att"] - 1.96 * w["se"]
        hi = w["ci_high"] if "ci_high" in w.columns else w["att"] + 1.96 * w["se"]
        ax.fill_between(w["rel_time"], lo, hi, alpha=0.15, color=color)

    ax.set_xlabel("Months since STR prohibition (threshold crossing)", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12, pad=12)
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-PLOT_PRE_MONTHS - 0.5, PLOT_POST_MONTHS + 0.5)


class CallawaySantAnnaHeterogeneityVisualizer(Visualizer):
    """Save heterogeneity overlay plots and summary CSV."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Configure output directory for heterogeneity figures and CSV."""
        super().__init__(
            "callaway_santanna_heterogeneity_visualizer",
            "Callaway & Sant'Anna heterogeneity plots",
        )
        self.output_dir = output_dir or "/project/output/did-cs"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Persist ``cs_heterogeneity_summary.csv`` and subgroup overlay PNGs."""
        het = context.get("cs_heterogeneity_results")
        if not het:
            logger.warning("cs_heterogeneity_results missing; skip heterogeneity viz.")
            return {}

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        splits = het.get("splits") or {}
        meta = het.get("meta") or {}
        summary = het.get("summary_table")
        if not isinstance(summary, pd.DataFrame):
            summary = pd.DataFrame()
        out_paths: dict[str, str] = {}

        # Summary CSV (always write so downstream tools see the path)
        p = Path(self.output_dir) / "cs_heterogeneity_summary.csv"
        summary.to_csv(p, index=False)
        out_paths["cs_heterogeneity_summary_csv"] = str(p)
        logger.info("Wrote %s (%d rows)", p, len(summary))

        # Income
        inc = splits.get("income")
        if inc and isinstance(inc.get("low"), dict):
            cut = _fmt_num(meta.get("median_income_cutoff"), ".0f")
            path = self._save_split_plot(
                inc,
                "did_cs_heterogeneity_income.png",
                "CS heterogeneity: median household income",
                (f"Below/equal median (${cut})", "low", "tab:blue"),
                (f"Above median (${cut})", "high", "tab:orange"),
            )
            if path:
                out_paths["cs_heterogeneity_income_plot"] = path

        # Renter share
        rs = splits.get("renter_share")
        if rs and isinstance(rs.get("low"), dict):
            cut = _fmt_num(meta.get("median_pct_rented_cutoff"), ".1f", suffix="%")
            path = self._save_split_plot(
                rs,
                "did_cs_heterogeneity_renter_share.png",
                "CS heterogeneity: renter share (% of occupied units rented)",
                (f"Below/equal median ({cut})", "low", "tab:blue"),
                (f"Above median ({cut})", "high", "tab:orange"),
            )
            if path:
                out_paths["cs_heterogeneity_renter_share_plot"] = path

        # Airbnb listing density (STR intensity proxy)
        ab = splits.get("airbnb_density")
        if ab and isinstance(ab.get("low"), dict):
            cut = _fmt_num(meta.get("median_airbnb_density_cutoff"), ".2f")
            path = self._save_split_plot(
                ab,
                "did_cs_heterogeneity_airbnb_density.png",
                "CS heterogeneity: Airbnb listing density (listings/km², winsorized)",
                (
                    f"Below/equal median density ({cut})",
                    "low",
                    "tab:blue",
                ),
                (f"Above median density ({cut})", "high", "tab:orange"),
            )
            if path:
                out_paths["cs_heterogeneity_airbnb_density_plot"] = path

        # Dose
        dose = splits.get("dose")
        if dose and isinstance(dose.get("low"), dict):
            cut = _fmt_num(meta.get("median_peak_pct_restricted_cutoff"), ".4f")
            path = self._save_split_plot(
                dose,
                "did_cs_heterogeneity_dose.png",
                "CS heterogeneity: peak prohibited share (max cumulative units / occupancy)",
                (f"Below/equal median peak ({cut})", "low", "tab:blue"),
                (f"Above median peak ({cut})", "high", "tab:orange"),
            )
            if path:
                out_paths["cs_heterogeneity_dose_plot"] = path

        # Early vs late
        ct = splits.get("cohort_timing")
        if ct and isinstance(ct.get("early"), dict):
            dcut = str(meta.get("median_first_treatment_month", ""))[:10] or "n/a"
            path = self._save_split_plot(
                ct,
                "did_cs_cohort_early_vs_late.png",
                "CS heterogeneity: early vs. late adopters (median first treatment month)",
                (f"Early (first treatment ≤ {dcut})", "early", "tab:green"),
                (f"Late (first treatment > {dcut})", "late", "tab:red"),
            )
            if path:
                out_paths["cs_cohort_early_vs_late_plot"] = path

        return out_paths

    def _save_split_plot(
        self,
        split: dict[str, Any],
        filename: str,
        plot_title: str,
        spec_a: tuple[str, str, str],
        spec_b: tuple[str, str, str],
    ) -> str | None:
        label_a, key_a, color_a = spec_a
        label_b, key_b, color_b = spec_b
        da = split.get(key_a) or {}
        db = split.get(key_b) or {}
        es_a = da.get("event_study")
        es_b = db.get("event_study")
        if (not isinstance(es_a, pd.DataFrame) or es_a.empty) and (
            not isinstance(es_b, pd.DataFrame) or es_b.empty
        ):
            logger.warning("No event-study data for %s; skip plot.", filename)
            return None

        fig, ax = plt.subplots(figsize=(10, 6))
        series: list[tuple[str, pd.DataFrame, str]] = [
            (
                label_a,
                es_a if isinstance(es_a, pd.DataFrame) else pd.DataFrame(),
                color_a,
            ),
            (
                label_b,
                es_b if isinstance(es_b, pd.DataFrame) else pd.DataFrame(),
                color_b,
            ),
        ]
        _plot_overlay_event_study(
            ax,
            series,
            plot_title,
            "ATT on rental price ($)",
        )
        out_path = Path(self.output_dir) / filename
        # Single title on axes only; avoid fig.suptitle (clips with bbox_inches=tight).
        setup_figure_and_save(fig, out_path, title=None, logger=logger)
        logger.info("Saved %s", out_path)
        return str(out_path)
