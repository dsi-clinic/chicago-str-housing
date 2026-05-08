"""SUTVA-style spillover probes: isolated vs adjacent never-treated + neighbour-share quartiles."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


def _run_cs_subset(
    analyzer: CallawaySantAnnaAnalyzer,
    panel: pd.DataFrame,
    never_kept: list[str],
    label: str,
) -> dict[str, Any]:
    """Pool selected never-treated tracts with all treated units and re-estimate pooled CS ATT."""
    ever = panel.groupby("tract_geoid")["treated"].max().astype(bool)
    treated_ids = ever[ever].index.astype(str).tolist()
    keep = sorted(set(treated_ids) | {str(x) for x in never_kept})
    subset = panel[panel["tract_geoid"].astype(str).isin(keep)].copy()
    row: dict[str, Any] = {
        "subgroup": label,
        "n_tracts": int(subset["tract_geoid"].nunique()),
        "n_never_kept": int(len(never_kept)),
        "att": float("nan"),
        "se": float("nan"),
    }
    if row["n_tracts"] < 12 or len(subset) < 800:
        logger.info("Skipping CS for %s: small subset (n_tr=%s obs=%s)", label, row["n_tracts"], len(subset))
        return row
    try:
        out = analyzer.execute({"did_panel": subset})
        oo = out.get("cs_overall_att") or {}
        row["att"] = float(oo.get("att", np.nan))
        row["se"] = float(oo.get("se", np.nan))
    except Exception as exc:
        logger.warning("CS subset %s failed: %s", label, exc)
    return row


def _dose_bins(
    analyzer: CallawaySantAnnaAnalyzer,
    nt_ids: list[str],
    share: dict[str, float],
    ever: pd.Series,
    panel: pd.DataFrame,
) -> pd.DataFrame:
    """Quartiles of mid-panel neighbour-treated share among never-treated; re-run CS per bin."""
    if len(nt_ids) < 16:
        return pd.DataFrame(
            [
                {
                    "quartile": "NA",
                    "label": "",
                    "n_never_tr": len(nt_ids),
                    "mean_neighbour_share_treated_mid": float("nan"),
                    "att": float("nan"),
                    "se": float("nan"),
                }
            ]
        )
    treated_ids = ever[ever].index.astype(str).tolist()
    s = pd.Series({k: float(share[k]) for k in nt_ids}, dtype=float)

    try:
        bin_labels = pd.qcut(s, q=4, duplicates="drop")
    except ValueError as exc:
        logger.warning("Could not quartile-split neighbour shares: %s", exc)
        return pd.DataFrame(
            [
                {
                    "quartile": "NA",
                    "label": "",
                    "n_never_tr": len(nt_ids),
                    "mean_neighbour_share_treated_mid": float(s.mean()) if len(s) else float("nan"),
                    "att": float("nan"),
                    "se": float("nan"),
                }
            ]
        )

    rows: list[dict[str, Any]] = []
    for iq, (_, sub) in enumerate(s.groupby(bin_labels, observed=True), start=1):
        lst = sorted(sub.index.astype(str).tolist())
        mean_share = float(sub.mean())
        subset = panel[panel["tract_geoid"].astype(str).isin(sorted(set(lst) | set(treated_ids)))].copy()
        r = {
            "quartile": str(iq),
            "label": f"Q{iq}",
            "n_never_tr": len(lst),
            "mean_neighbour_share_treated_mid": mean_share,
            "att": float("nan"),
            "se": float("nan"),
        }
        if subset["tract_geoid"].nunique() >= 12 and len(subset) >= 800:
            try:
                out = analyzer.execute({"did_panel": subset})
                oo = out.get("cs_overall_att") or {}
                r["att"] = float(oo.get("att", np.nan))
                r["se"] = float(oo.get("se", np.nan))
            except Exception as exc:
                logger.warning("Dose quartile Q%s failed: %s", iq, exc)
        rows.append(r)
    return pd.DataFrame(rows)


_PRETTY_SUBGROUP = {
    "never_isolated_neighbours": "Isolated never-treated\n(no treated neighbour)",
    "never_adjacent_treated_neighbour": "Adjacent never-treated\n(>=1 treated neighbour)",
    "full_sample": "Full sample\n(all never-treated)",
}


def _forest_plot(df: pd.DataFrame, baseline: float, path: Path) -> None:
    if df.dropna(subset=["att"]).empty:
        return
    dd = df.dropna(subset=["att"]).reset_index(drop=True)
    errs = dd["se"].astype(float).fillna(0) * 1.96
    ypos = np.arange(len(dd))
    labels = [_PRETTY_SUBGROUP.get(str(s), str(s).replace("_", " ")) for s in dd["subgroup"]]

    plt.figure(figsize=(8.8, max(3.4, 1.6 + 0.7 * len(dd))))
    if baseline == baseline:  # not NaN
        plt.axvline(float(baseline), color="grey", linestyle=":", linewidth=1.5, label="Full-sample CS ATT")
    plt.errorbar(
        dd["att"].astype(float),
        ypos,
        xerr=errs.clip(lower=0),
        fmt="o",
        capsize=4,
        color="#800000",
        markersize=7,
        linewidth=1.5,
    )
    plt.yticks(ypos, labels)
    plt.xlabel("ATT ($/month, rent index scale)")
    plt.title("SUTVA probe: donut comparison groups")
    plt.legend(loc="lower right", framealpha=0.9)
    plt.grid(axis="x", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


def _dose_plot(dose: pd.DataFrame, path: Path) -> None:
    if dose.dropna(subset=["att"]).empty:
        return
    d = dose.dropna(subset=["att"]).reset_index(drop=True)
    xs = np.arange(len(d))

    plt.figure(figsize=(7.5, 4.8))
    plt.axhline(0.0, color="lightgray", linestyle="--")
    errs = (d["se"].astype(float).fillna(0) * 1.96).to_numpy()

    lbl = (
        d["label"].astype(str)
        if "label" in d.columns
        else d["quartile"].astype(str)
    )
    plt.errorbar(xs, d["att"].astype(float), yerr=errs, fmt="o-", capsize=4, color="#800000")

    plt.xticks(xs, lbl, rotation=0)
    plt.xlabel("Never-treated quartile by neighbour-treated share at mid-sample")
    plt.ylabel("Pooled CS ATT ($/month)")
    plt.title("Neighbour-share exposure (dose) and pooled ATT")

    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()


class SUTVADonutDoseAnalyzer(Analyzer):
    """Re-run pooled CS on spatial subsamples of never-treated tracts."""

    def __init__(
        self,
        output_dir: str | Path,
        comparison_group: str = "nevertreated",
        anticipation: int = 0,
        min_cohort_size: int = 5,
    ) -> None:
        super().__init__(
            "sutva_donut_dose_analysis",
            "Spatial donut / dose-response style neighbourhood exposure checks",
        )
        self.output_dir = Path(output_dir)
        self.comparison_group = comparison_group
        self.anticipation = anticipation
        self.min_cohort_size = min_cohort_size

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        pdf = context.get("did_panel")
        gdf = context.get("tract_boundaries")
        baseline = context.get("cs_overall_att") or {}

        self.output_dir.mkdir(parents=True, exist_ok=True)
        if pdf is None or gdf is None:
            logger.warning("sutva: missing did_panel or tract_boundaries")
            return {}

        panel = pdf.copy()
        panel["tract_geoid"] = panel["tract_geoid"].astype(str)
        tg = np.sort(panel["tract_geoid"].unique())

        mids = sorted(panel["month"].unique())
        mc = mids[len(mids) // 2]
        midslice = panel[panel["month"] == mc][["tract_geoid", "treated"]].drop_duplicates("tract_geoid")
        mser = midslice.set_index("tract_geoid")["treated"].astype(float)

        ever = panel.groupby("tract_geoid")["treated"].max().astype(bool)

        bx = gdf[gdf["tract_geoid"].astype(str).isin(tg)].copy()
        bx["tract_geoid"] = bx["tract_geoid"].astype(str)
        bx = bx.set_index("tract_geoid")

        neighbours: dict[str, set[str]] = {}
        for t in tg:
            tg_s = str(t)
            gm = bx.loc[tg_s].geometry if tg_s in bx.index else None
            if gm is None:
                neighbours[tg_s] = set()
                continue
            tn = bx.index[bx.geometry.touches(gm)]
            neighbours[tg_s] = {str(x) for x in tn if str(x) != tg_s}

        nt_all: list[str] = []
        iso: list[str] = []
        adj: list[str] = []
        for tg_s in tg.astype(str):
            if tg_s not in ever.index or bool(ever.loc[tg_s]):
                continue
            nt_all.append(tg_s)
            neigh = neighbours.get(tg_s, set())
            if len(neigh) == 0:
                iso.append(tg_s)
                continue
            has_treated_neighbour = any(nb in ever.index and bool(ever.loc[nb]) for nb in neigh)
            if has_treated_neighbour:
                adj.append(tg_s)
            else:
                iso.append(tg_s)

        # Recompute share for all tracts (used for dose on nt_all)
        share = {}
        for tg_s in tg.astype(str):
            neigh = neighbours.get(tg_s, set())
            if len(neigh) == 0:
                share[tg_s] = 0.0
            else:
                treated_neigh_at_mid = sum(
                    1 for n in neigh if n in mser.index and float(mser.loc[n]) >= 0.5
                )
                share[tg_s] = treated_neigh_at_mid / len(neigh)

        analyzer = CallawaySantAnnaAnalyzer(
            comparison_group=self.comparison_group,
            anticipation=self.anticipation,
            min_cohort_size=self.min_cohort_size,
        )

        donut = [
            _run_cs_subset(analyzer, panel, iso, "never_isolated_neighbours"),
            _run_cs_subset(analyzer, panel, adj, "never_adjacent_treated_neighbour"),
            {
                "subgroup": "full_sample",
                "n_never_kept": float("nan"),
                "n_tracts": float("nan"),
                "att": float(baseline.get("att", np.nan)),
                "se": float(baseline.get("se", np.nan)),
            },
        ]
        dose = _dose_bins(analyzer, nt_all, share, ever, panel)

        donut_df = pd.DataFrame(donut)
        donut_df.to_csv(self.output_dir / "sutva_donut_summary.csv", index=False)
        dose.to_csv(self.output_dir / "sutva_dose_quartiles.csv", index=False)

        _forest_plot(donut_df.dropna(subset=["att"]), float(baseline.get("att", np.nan)), self.output_dir / "sutva_donut.png")
        _dose_plot(dose, self.output_dir / "sutva_dose_response.png")

        return {
            "sutva_donut_summary": donut_df,
            "sutva_dose_quartiles": dose,
        }
