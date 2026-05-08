"""Policy-facing funnel graphic: raw panel → matched DiD panel → cohort count."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)



class DataFunnelVisualizer(Visualizer):
    """Write ``data_funnel.png``: three-stage funnel with matched split + cohort bars."""

    def __init__(self, output_dir: str | Path) -> None:
        super().__init__(
            "data_funnel_visualization",
            "Matplotlib funnel: raw → matched → CS cohorts",
        )
        self.output_dir = Path(output_dir)

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        panel_raw = self.output_dir / "did_panel_data.csv"
        panel_ov = self.output_dir / "did_descriptive_panel_overview.csv"
        cohort_csv = self.output_dir / "did_descriptive_cohort_stats.csv"

        if not panel_raw.exists() or not panel_ov.exists():
            logger.warning("data_funnel: missing did_panel_data or panel overview CSV")
            return {}

        pdf_raw = pd.read_csv(
            panel_raw, usecols=["tract_geoid", "treated"], low_memory=False
        )
        tg = pdf_raw.groupby("tract_geoid")["treated"].max()
        n_raw = int(tg.index.nunique())
        n_raw_t = int((tg >= 1).sum())
        n_raw_nt = n_raw - n_raw_t

        row_ov = pd.read_csv(panel_ov).iloc[0].to_dict()
        n_ma = int(row_ov.get("n_tracts", 0))
        n_ma_t = int(row_ov.get("tracts_eventually_treated", 0))
        n_ma_nt = int(row_ov.get("tracts_never_treated", 0))

        cohort_labels: list[str] = []
        cohort_ns: list[int] = []
        if cohort_csv.exists():
            cdf = pd.read_csv(cohort_csv)
            if not cdf.empty:
                for _, rw in cdf.iterrows():
                    m_raw = str(rw.get("first_prohibition_month", ""))
                    ym = m_raw[:7] if len(m_raw) >= 7 else m_raw
                    cohort_labels.append(ym)
                    cohort_ns.append(int(rw["n_tracts"]))

        maroon = "#800000"
        gray = "#262626"
        ctrl = "#1f4e79"
        trt = maroon

        fig = plt.figure(figsize=(14, 5.2), facecolor="white")
        gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.25], wspace=0.32)

        # --- Stage A: raw ---
        ax0 = fig.add_subplot(gs[0, 0])
        ax0.barh(
            0,
            n_raw_nt,
            left=0,
            height=0.55,
            color=ctrl,
            edgecolor="white",
            label="Never-treated",
        )
        ax0.barh(
            0,
            n_raw_t,
            left=n_raw_nt,
            height=0.55,
            color=trt,
            edgecolor="white",
            label="Ever-treated",
        )
        ax0.set_xlim(0, max(n_raw, 1) * 1.08)
        ax0.set_yticks([])
        ax0.set_xlabel("Tracts", fontsize=10, color=gray)
        ax0.set_title(f"A. Raw panel\n({n_raw} tracts)", fontsize=11, color=maroon, fontweight="semibold")
        ax0.text(
            n_raw_nt / 2,
            0,
            str(n_raw_nt),
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="semibold",
        )
        ax0.text(
            n_raw_nt + n_raw_t / 2,
            0,
            str(n_raw_t),
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="semibold",
        )
        ax0.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=8)
        ax0.spines["top"].set_visible(False)
        ax0.spines["right"].set_visible(False)

        # --- Stage B: matched ---
        ax1 = fig.add_subplot(gs[0, 1])
        ax1.barh(
            0,
            n_ma_nt,
            left=0,
            height=0.55,
            color=ctrl,
            edgecolor="white",
        )
        ax1.barh(
            0,
            n_ma_t,
            left=n_ma_nt,
            height=0.55,
            color=trt,
            edgecolor="white",
        )
        ax1.set_xlim(0, max(n_ma, n_raw, 1) * 1.08)
        ax1.set_yticks([])
        ax1.set_xlabel("Tracts", fontsize=10, color=gray)
        ax1.set_title(
            f"B. Matched DiD panel\n({n_ma} tracts)",
            fontsize=11,
            color=maroon,
            fontweight="semibold",
        )
        ax1.text(
            n_ma_nt / 2 if n_ma_nt else 0,
            0,
            str(n_ma_nt),
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="semibold",
        )
        ax1.text(
            n_ma_nt + n_ma_t / 2,
            0,
            str(n_ma_t),
            ha="center",
            va="center",
            color="white",
            fontsize=10,
            fontweight="semibold",
        )
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)

        # --- Stage C: cohort sizes ---
        ax2 = fig.add_subplot(gs[0, 2])
        if cohort_labels and cohort_ns:
            y_pos = range(len(cohort_labels))
            ax2.barh(
                list(y_pos),
                cohort_ns,
                color=trt,
                edgecolor="white",
                height=0.65,
            )
            ax2.set_yticks(list(y_pos))
            ax2.set_yticklabels(cohort_labels, fontsize=9)
            ax2.invert_yaxis()
            ax2.set_xlabel("Treated tracts per cohort", fontsize=10, color=gray)
            ax2.set_title(
                f"C. CS cohorts ($\\geq 5$ tracts)\n({len(cohort_labels)} months)",
                fontsize=11,
                color=maroon,
                fontweight="semibold",
            )
            for i, n in enumerate(cohort_ns):
                ax2.text(
                    n + max(cohort_ns) * 0.02,
                    i,
                    str(n),
                    va="center",
                    fontsize=9,
                    color=gray,
                )
            ax2.set_xlim(0, max(cohort_ns) * 1.22)
        else:
            ax2.text(
                0.5,
                0.5,
                "(No cohort CSV)",
                ha="center",
                va="center",
                transform=ax2.transAxes,
            )
            ax2.set_axis_off()

        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)

        fig.suptitle(
            "How we narrow to the analysis sample (tract counts)",
            fontsize=13,
            fontweight="semibold",
            color=gray,
            y=1.05,
        )
        fig.text(
            0.5,
            0.02,
            "Matched panel keeps all treated tracts; removes never-treated tracts whose pre-rent slope "
            "does not match any treated tract (k=3 nearest slopes).",
            ha="center",
            fontsize=9,
            color="#555555",
            style="italic",
        )

        out_path = self.output_dir / "data_funnel.png"
        plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        logger.info("Wrote %s", out_path)
        return {"data_funnel_plot": str(out_path)}
