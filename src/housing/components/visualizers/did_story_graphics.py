"""Publication-style DiD sample / matching / adoption figures (reusable PNGs)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from housing.components.visualizers.did_matplotlib_theme import (
    COLORS,
    configure_did_matplotlib_style,
)
from pipeline.base import Visualizer

logger = logging.getLogger(__name__)

_MIN_GROUPS_VIOLIN = 2
_MIN_OBS_PER_VIOLIN_GROUP = 5


class DIDStoryGraphicsVisualizer(Visualizer):
    """Write ``did_story_*.png`` from lineage, matching diagnostics, and trends."""

    def __init__(self, output_dir: str | Path) -> None:
        """Initialize the story graphics visualizer.

        Args:
            output_dir: Base directory for PNG outputs (same as DiD CSV folder).
        """
        super().__init__(
            "did_story_graphics",
            "Storytelling figures: tract funnel, matching balance, trends, adoption",
        )
        self.output_dir = Path(output_dir)
        self.required_data: list[str] = []

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Build ``did_story_*.png`` artefacts; missing inputs are skipped quietly."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        configure_did_matplotlib_style()

        paths: dict[str, str] = {}

        p1 = self._plot_sample_lineage(context.get("sample_lineage"))
        if p1:
            paths["did_story_sample_lineage"] = p1

        p2 = self._plot_trends_scatter(context.get("trends_df"))
        if p2:
            paths["did_story_pre_trends_scatter"] = p2

        p3 = self._plot_love(context)
        if p3:
            paths["did_story_matching_love"] = p3

        p4 = self._plot_control_reuse(context)
        if p4:
            paths["did_story_control_reuse"] = p4

        p5 = self._plot_cumulative_adoption(context)
        if p5:
            paths["did_story_cumulative_adoption"] = p5

        p6 = self._plot_pre_rent_violin(context.get("did_panel"))
        if p6:
            paths["did_story_pre_rent_violin"] = p6

        logger.info("did_story_graphics: wrote %d figure(s)", len(paths))
        return paths

    def _plot_sample_lineage(self, lineage: object) -> str | None:
        if lineage is None or not isinstance(lineage, pd.DataFrame):
            return None
        lineage_df = lineage.copy()
        if lineage_df.empty or "n_tracts" not in lineage_df.columns:
            return None
        work = lineage_df[lineage_df["n_tracts"].notna()].copy()
        if work.empty:
            return None
        work = work.sort_values(
            "stage_code" if "stage_code" in work.columns else "stage_label",
        )
        labels = work["stage_label"].astype(str).tolist()
        nvals = work["n_tracts"].astype(float).tolist()
        y = np.arange(len(labels))

        fig, ax = plt.subplots(figsize=(9.5, max(3.5, 0.45 * len(labels))))
        colors = [COLORS["control_light"]] * (len(labels) - 1) + [COLORS["treated"]]
        if len(labels) == 1:
            colors = [COLORS["treated"]]
        ax.barh(y, nvals, color=colors, edgecolor="white", height=0.72, alpha=0.92)
        for yi, nv in zip(y, nvals):
            ax.text(
                nv + max(nvals) * 0.015,
                yi,
                f"{int(nv):,}",
                va="center",
                fontsize=9,
                color=COLORS["neutral"],
            )
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("Unique tracts at this stage", fontsize=10)
        ax.set_title(
            "How the tract sample narrows (crosswalk → rents → matching)",
            fontsize=12,
            fontweight="semibold",
            pad=12,
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        out = self.output_dir / "did_story_sample_lineage.png"
        fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return str(out)

    def _plot_trends_scatter(self, trends_df: object) -> str | None:
        if trends_df is None or not isinstance(trends_df, pd.DataFrame):
            return None
        if trends_df.empty or "ever_treated" not in trends_df.columns:
            return None
        need = {"pre_trend_slope", "avg_pre_rent"}
        if not need.issubset(trends_df.columns):
            return None

        fig, ax = plt.subplots(figsize=(7.2, 6.0))
        for flag, label, c, m in (
            (0, "Never-treated (pre-period)", COLORS["control"], "o"),
            (1, "Ever-treated (pre-period)", COLORS["treated"], "s"),
        ):
            sub = trends_df[trends_df["ever_treated"] == flag]
            if sub.empty:
                continue
            ax.scatter(
                sub["avg_pre_rent"],
                sub["pre_trend_slope"],
                s=38,
                alpha=0.55,
                c=c,
                marker=m,
                edgecolors="white",
                linewidths=0.4,
                label=f"{label} (n={len(sub)})",
            )
        ax.axhline(0.0, color=COLORS["muted"], linewidth=0.8, linestyle="--", alpha=0.7)
        ax.set_xlabel("Average pre-treatment rent ($/mo)", fontsize=10)
        ax.set_ylabel("Pre-treatment rent slope ($/mo per month)", fontsize=10)
        ax.set_title(
            "Tracts in pre-trend space (features used in matching)",
            fontsize=12,
            fontweight="semibold",
            pad=10,
        )
        ax.legend(loc="best", fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        out = self.output_dir / "did_story_pre_trends_scatter.png"
        fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return str(out)

    def _plot_love(self, context: dict[str, Any]) -> str | None:
        """Horizontal Love-style plot: SMD before vs after matching on trend features."""
        path_csv = self.output_dir / "did_story_matching_balance_long.csv"
        if path_csv.exists():
            long_df = pd.read_csv(path_csv)
        else:
            long_df = self._love_from_context(context.get("matching_diagnostics"))
        if long_df is None or long_df.empty:
            return None

        fig, ax = plt.subplots(figsize=(6.5, 2.2 + 0.55 * len(long_df)))
        y = np.arange(len(long_df))
        labels = long_df["feature_label"].tolist()
        before = long_df["smd_before"].astype(float)
        after = long_df["smd_after"].astype(float)
        ax.axvline(0.0, color="#BBBBBB", linewidth=0.9, zorder=0)
        ax.axvline(-0.1, color="#DDDDDD", linewidth=0.7, linestyle=":", zorder=0)
        ax.axvline(0.1, color="#DDDDDD", linewidth=0.7, linestyle=":", zorder=0)
        ax.scatter(
            before,
            y - 0.12,
            s=70,
            color=COLORS["before"],
            marker="o",
            zorder=2,
            label="Before matching (all controls)",
            edgecolors="white",
        )
        ax.scatter(
            after,
            y + 0.12,
            s=70,
            color=COLORS["after"],
            marker="D",
            zorder=2,
            label="After matching (matched controls)",
            edgecolors="white",
        )
        for yi, b, a in zip(y, before, after):
            ax.plot(
                [b, a], [yi - 0.12, yi + 0.12], color="#AAAAAA", linewidth=0.8, zorder=1
            )
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=10)
        ax.set_xlabel("Standardized mean difference (pooled SD)", fontsize=10)
        ax.set_title(
            "Balance on matching features (tract level, pre-treatment)",
            fontsize=12,
            fontweight="semibold",
            pad=10,
        )
        ax.legend(loc="lower right", fontsize=8.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        out = self.output_dir / "did_story_matching_love.png"
        fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return str(out)

    @staticmethod
    def _love_from_context(matching_diag: object) -> pd.DataFrame | None:
        if not matching_diag or not isinstance(matching_diag, dict):
            return None
        raw = matching_diag.get("matching_features") or ""
        feats = [f.strip() for f in str(raw).split(",") if f.strip()]
        rows = []
        for feat in feats:
            b = matching_diag.get(f"smd_{feat}_before")
            a = matching_diag.get(f"smd_{feat}_after")
            if b is None and a is None:
                continue
            rows.append(
                {
                    "feature": feat,
                    "feature_label": feat.replace("_", " ").title(),
                    "smd_before": b,
                    "smd_after": a,
                },
            )
        return pd.DataFrame(rows) if rows else None

    def _plot_control_reuse(self, context: dict[str, Any]) -> str | None:
        reuse = context.get("matching_diagnostics", {}) or {}
        table = reuse.get("control_reuse_table")
        if table is None or not isinstance(table, pd.DataFrame) or table.empty:
            p = self.output_dir / "did_matching_control_reuse.csv"
            if p.exists():
                table = pd.read_csv(p)
            else:
                return None
        if "n_treated_matches" not in table.columns:
            return None

        fig, ax = plt.subplots(figsize=(6.8, 4.2))
        counts = table["n_treated_matches"].value_counts().sort_index()
        ax.bar(
            counts.index.astype(float),
            counts.values,
            color=COLORS["accent"],
            edgecolor="white",
            width=0.85,
            alpha=0.9,
        )
        ax.set_xlabel(
            "Number of treated tracts matched to the same control", fontsize=10
        )
        ax.set_ylabel("Number of control tracts", fontsize=10)
        ax.set_title(
            "Control reuse (nearest-neighbour matching)",
            fontsize=12,
            fontweight="semibold",
            pad=10,
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        out = self.output_dir / "did_story_control_reuse.png"
        fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return str(out)

    def _plot_cumulative_adoption(self, context: dict[str, Any]) -> str | None:
        cum = context.get("cumulative_adoption")
        if cum is None or not isinstance(cum, pd.DataFrame) or cum.empty:
            cum = self._load_cumulative_adoption_csv()
        if cum is None or cum.empty or "cumulative_treated" not in cum.columns:
            return None

        fig, ax = plt.subplots(figsize=(8.0, 4.0))
        x = pd.to_datetime(cum.index)
        y = cum["cumulative_treated"].astype(float)
        ax.fill_between(x, y, alpha=0.25, color=COLORS["treated"])
        ax.plot(
            x,
            y,
            color=COLORS["treated"],
            linewidth=2.0,
            label="Cumulative treated tracts",
        )
        ax.set_xlabel("Month", fontsize=10)
        ax.set_ylabel("Count of tracts with prohibition", fontsize=10)
        ax.set_title(
            "STR prohibition adoption (tracts, cumulative)",
            fontsize=12,
            fontweight="semibold",
        )
        ax.legend(loc="upper left", fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.autofmt_xdate()
        out = self.output_dir / "did_story_cumulative_adoption.png"
        fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return str(out)

    def _load_cumulative_adoption_csv(self) -> pd.DataFrame | None:
        p = self.output_dir / "did_descriptive_cumulative_adoption.csv"
        if not p.exists():
            return None
        raw = pd.read_csv(p)
        if "cumulative_treated" not in raw.columns:
            return None
        idx_col = "month" if "month" in raw.columns else raw.columns[0]
        out = raw.set_index(idx_col)
        out.index = pd.to_datetime(out.index, errors="coerce")
        return out

    def _plot_pre_rent_violin(self, did_panel: object) -> str | None:
        if did_panel is None or not isinstance(did_panel, pd.DataFrame):
            return None
        dp = did_panel.copy()
        dp["month"] = pd.to_datetime(dp["month"])
        if "ever_treated" not in dp.columns:
            dp["ever_treated"] = (
                dp.groupby("tract_geoid")["treated"].transform("max").astype(int)
            )
        first_t = dp.loc[dp["treated"] == 1, "month"].min()
        if pd.isna(first_t):
            return None
        pre = dp[dp["month"] < first_t]
        parts = []
        for lab, val in (("Never-treated", 0), ("Ever-treated", 1)):
            s = pre.loc[pre["ever_treated"] == val, "rental_price"].dropna()
            if len(s) > _MIN_OBS_PER_VIOLIN_GROUP:
                parts.append((lab, s))

        if len(parts) < _MIN_GROUPS_VIOLIN:
            return None

        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        positions = [1, 2]
        vp = ax.violinplot(
            [p[1] for p in parts],
            positions=positions[: len(parts)],
            showmeans=True,
            showmedians=False,
            widths=0.62,
        )
        for i, b in enumerate(vp["bodies"]):
            b.set_facecolor(COLORS["control"] if i == 0 else COLORS["treated"])
            b.set_edgecolor("white")
            b.set_alpha(0.68)
        if "cmeans" in vp:
            vp["cmeans"].set_colors(COLORS["treated"])
        ax.set_xticks(positions[: len(parts)])
        ax.set_xticklabels([p[0] for p in parts], fontsize=10)
        ax.set_ylabel("Rent ($/mo, tract-month)", fontsize=10)
        ax.set_title(
            "Pre-treatment rent distribution (matched sample)",
            fontsize=12,
            fontweight="semibold",
            pad=10,
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        out = self.output_dir / "did_story_pre_rent_violin.png"
        fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return str(out)
