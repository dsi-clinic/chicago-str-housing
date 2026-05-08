"""One figure juxtaposing pooled CS curves and raw-rent cohort paths."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

PLOT_PRE = 12
PLOT_POST = 36


class CohortDynamicsExplainerVisualizer(Visualizer):
    """Overlay baseline vs residualized CS event studies plus largest-cohort rents."""

    def __init__(self, output_dir: str | Path | None = None) -> None:
        super().__init__(
            "cohort_dynamics_explainer",
            "Cohort heterogeneity narrative: CS curves + raw rents for top cohorts",
        )
        self.output_dir = Path(output_dir or "/project/output")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        base = context.get("cs_event_study")
        ctrl = context.get("cs_event_study_with_controls")
        cohort_info = context.get("cs_cohort_info") or {}

        panel = context.get("did_panel")
        if panel is None or base is None or base.empty:
            logger.warning("cohort_explainer: missing cs_event_study or did_panel")
            return {}

        cohort_sizes = cohort_info.get("cohort_sizes")
        cohort_df = cohort_info.get("treated_cohorts")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        plot_base = base[
            (base["rel_time"] >= -PLOT_PRE) & (base["rel_time"] <= PLOT_POST)
        ].copy()

        plt.figure(figsize=(12.5, 11))
        ax1 = plt.subplot2grid((3, 1), (0, 0), rowspan=1)

        ax1.axvspan(-PLOT_PRE, -1, alpha=0.12, color="gray", label=None)
        ax1.axhline(0, color="lightgray", linestyle="--", linewidth=1)
        ax1.axvline(0, color="#800000", linestyle=":", linewidth=1.5)

        ax1.plot(
            plot_base["rel_time"],
            plot_base["att"],
            color="#34495e",
            marker="o",
            markersize=4,
            label="CS pooled (rent levels)",
        )
        ax1.fill_between(
            plot_base["rel_time"],
            plot_base["ci_low"],
            plot_base["ci_high"],
            color="#34495e",
            alpha=0.15,
            linewidth=0,
        )

        if ctrl is not None and not ctrl.empty:
            cw = ctrl[
                (ctrl["rel_time"] >= -PLOT_PRE) & (ctrl["rel_time"] <= PLOT_POST)
            ].copy()
            ax1.plot(
                cw["rel_time"],
                cw["att"],
                color="#800000",
                marker="s",
                markersize=4,
                label="CS + covariates + tract trends (residualized)",
            )
            ax1.fill_between(
                cw["rel_time"],
                cw["ci_low"],
                cw["ci_high"],
                color="#800000",
                alpha=0.12,
                linewidth=0,
            )

        ax1.set_xlabel(r"Months since first prohibition (tract)")
        ax1.set_ylabel("ATT ($)")
        ax1.grid(True, alpha=0.35)
        ax1.legend(loc="best", fontsize=8)
        ax1.set_title("A. Pooled ATT: baseline vs preconditioned outcomes")

        # --- Bottom: raw average rents for largest cohorts vs never-treated ---
        ax_bot = plt.subplot2grid((3, 1), (1, 0), rowspan=2)

        pdata = panel.copy()
        pdata["tract_geoid"] = pdata["tract_geoid"].astype(str)
        ever = pdata.groupby("tract_geoid")["treated"].max().astype(bool)
        never_avg = (
            pdata[pdata["tract_geoid"].isin(ever[~ever].index)][["month", "rental_price"]]
            .groupby("month")["rental_price"]
            .mean()
        )

        if cohort_sizes is not None and cohort_df is not None and not cohort_sizes.empty:
            top_cohorts = cohort_sizes.sort_values(ascending=False).head(4).index.to_list()

            cmap = plt.cm.tab10(np.linspace(0, 1, len(top_cohorts)))
            for rank, cohort_date in enumerate(top_cohorts):
                tg = cohort_df[
                    cohort_df["first_treatment_month"] == cohort_date
                ]["tract_geoid"].astype(str)

                rents = (
                    pdata[pdata["tract_geoid"].isin(tg)][["month", "rental_price"]]
                    .groupby("month")["rental_price"]
                    .mean()
                )
                label = f"Treated cohort {pd.Timestamp(cohort_date).strftime('%Y-%m')} (n={len(tg)})"
                rents.plot(ax=ax_bot, color=cmap[rank], linewidth=1.9, label=label)

            never_avg.plot(ax=ax_bot, color="black", linewidth=2.0, linestyle="--", label="Never treated (matched)")

        ax_bot.grid(True, alpha=0.3)
        ax_bot.set_title("B. Mean raw rent trajectories — largest prohibition cohorts")
        ax_bot.set_ylabel(r"Rent index (\$/month)")
        ax_bot.set_xlabel("Month")
        ax_bot.tick_params(axis="x", rotation=35)
        ax_bot.legend(loc="upper left", fontsize=8, ncol=2)

        plt.subplots_adjust(top=0.96, bottom=0.08, left=0.08, right=0.98, hspace=0.42)
        out_png = self.output_dir / "cohort_dynamics_explainer.png"
        plt.savefig(out_png, dpi=240, bbox_inches="tight")
        plt.close()

        csv_path = self.output_dir / "cohort_dynamics_explainer_data.csv"
        plot_base.rename(columns={"att": "att_baseline_CS"}).to_csv(csv_path, index=False)

        logger.info("Cohort dynamics explainer saved to %s", out_png)
        return {"cohort_dynamics_explainer_plot": str(out_png), "cohort_explainer_csv": str(csv_path)}
