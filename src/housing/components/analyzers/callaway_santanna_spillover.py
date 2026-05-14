"""Spatial spillover analysis: adjacent never-treated vs pure controls (CS).

Never-treated tracts that share a Queen edge with any treated tract are
reclassified as "spillover" units with treatment timing inherited from the
earliest ``treatment_start_month`` among treated neighbors. Original treated
tracts are excluded; CS is re-estimated on spillover vs never-treated with no
treated neighbor (pure controls).
"""

from __future__ import annotations

import logging
from typing import Any

import geopandas as gpd
import pandas as pd
from libpysal.weights import Queen

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


def _treated_geoids(panel: pd.DataFrame) -> set[str]:
    ever = panel.groupby("tract_geoid", observed=True)["treated"].max()
    return {str(x) for x in ever[ever == 1].index.tolist()}


def _never_treated_geoids(panel: pd.DataFrame) -> set[str]:
    ever = panel.groupby("tract_geoid", observed=True)["treated"].max()
    return {str(x) for x in ever[ever == 0].index.tolist()}


def _treatment_start_month_by_tract(panel: pd.DataFrame) -> pd.Series:
    """Per treated tract: first month with treated == 1 (aligns with CS cohorts)."""
    t = panel.loc[panel["treated"] == 1, ["tract_geoid", "month"]].copy()
    t["tract_geoid"] = t["tract_geoid"].astype(str)
    return t.groupby("tract_geoid", observed=True)["month"].min()


def _build_queen_weights(tract_boundaries: gpd.GeoDataFrame) -> Queen:
    """Queen contiguity on full tract layer (Cook) so neighbors outside a subset exist."""
    gdf = tract_boundaries.copy()
    if "tract_geoid" not in gdf.columns:
        raise ValueError("tract_boundaries must include tract_geoid")
    gdf["tract_geoid"] = gdf["tract_geoid"].astype(str)
    gdf = gdf.drop_duplicates(subset=["tract_geoid"]).set_index("tract_geoid")
    return Queen.from_dataframe(gdf, use_index=True)


class CallawaySantAnnaSpilloverAnalyzer(Analyzer):
    """Estimate CS on a spillover panel (adjacent never-treated vs pure controls)."""

    def __init__(
        self,
        comparison_group: str = "nevertreated",
        anticipation: int = 0,
        min_cohort_size: int = 5,
    ) -> None:
        """Initialize spillover analyzer (CS settings match baseline pipeline)."""
        super().__init__(
            "callaway_santanna_spillover_analysis",
            "Callaway & Sant'Anna spillover: adjacent never-treated vs pure controls",
        )
        self.comparison_group = comparison_group
        self.anticipation = anticipation
        self.min_cohort_size = min_cohort_size

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Classify never-treated tracts by adjacency, build spillover panel, run CS."""
        did_panel = context.get("did_panel")
        tract_boundaries = context.get("tract_boundaries")
        if did_panel is None or did_panel.empty:
            raise ValueError("did_panel not found or empty")
        if tract_boundaries is None or tract_boundaries.empty:
            raise ValueError("tract_boundaries not found or empty")

        panel = did_panel.copy()
        panel["tract_geoid"] = panel["tract_geoid"].astype(str)

        treated_ids = _treated_geoids(panel)
        never_ids = _never_treated_geoids(panel)
        first_treat = _treatment_start_month_by_tract(panel)

        w = _build_queen_weights(tract_boundaries)
        id_order = {str(i) for i in w.id_order}

        classification_rows: list[dict[str, Any]] = []
        spillover_geoids: list[str] = []
        pure_geoids: list[str] = []
        missing_geom: list[str] = []

        for tid in sorted(treated_ids):
            classification_rows.append(
                {
                    "tract_geoid": tid,
                    "category": "treated",
                    "n_treated_neighbors": pd.NA,
                    "in_shapefile": tid in id_order,
                    "inherited_treatment_month": pd.NaT,
                }
            )

        for nt in sorted(never_ids):
            in_shp = nt in id_order
            if not in_shp:
                missing_geom.append(nt)
                classification_rows.append(
                    {
                        "tract_geoid": nt,
                        "category": "no_geometry",
                        "n_treated_neighbors": 0,
                        "in_shapefile": False,
                        "inherited_treatment_month": pd.NaT,
                    }
                )
                continue

            neigh = [str(n) for n in w.neighbors.get(nt, [])]
            treated_neigh = [n for n in neigh if n in treated_ids]
            n_tn = len(treated_neigh)

            if n_tn == 0:
                pure_geoids.append(nt)
                classification_rows.append(
                    {
                        "tract_geoid": nt,
                        "category": "pure_control",
                        "n_treated_neighbors": 0,
                        "in_shapefile": True,
                        "inherited_treatment_month": pd.NaT,
                    }
                )
            else:
                spillover_geoids.append(nt)
                inherited = first_treat.reindex(treated_neigh).min()
                classification_rows.append(
                    {
                        "tract_geoid": nt,
                        "category": "spillover",
                        "n_treated_neighbors": n_tn,
                        "in_shapefile": True,
                        "inherited_treatment_month": inherited,
                    }
                )

        classification = pd.DataFrame(classification_rows)
        if missing_geom:
            logger.warning(
                "Spillover: %d never-treated tracts missing from shapefile; excluded from CS panel",
                len(missing_geom),
            )

        meta: dict[str, Any] = {
            "n_treated": len(treated_ids),
            "n_never_treated": len(never_ids),
            "n_spillover": len(spillover_geoids),
            "n_pure_control": len(pure_geoids),
            "n_never_missing_geometry": len(missing_geom),
            "comparison_group": self.comparison_group,
            "min_cohort_size": self.min_cohort_size,
        }
        logger.info(
            "Spillover classification: treated=%d, spillover=%d, pure_control=%d",
            meta["n_treated"],
            meta["n_spillover"],
            meta["n_pure_control"],
        )

        keep_geoids = set(spillover_geoids) | set(pure_geoids)
        spill_panel = panel[panel["tract_geoid"].isin(keep_geoids)].copy()

        inherited_series = classification.loc[
            classification["category"] == "spillover",
            ["tract_geoid", "inherited_treatment_month"],
        ].set_index("tract_geoid")["inherited_treatment_month"]

        spill_panel["treated"] = 0
        is_spill = spill_panel["tract_geoid"].isin(spillover_geoids)
        inherited_start = spill_panel.loc[is_spill, "tract_geoid"].map(inherited_series)
        spill_panel.loc[is_spill, "treated"] = (
            spill_panel.loc[is_spill, "month"] >= inherited_start
        ).astype(int)
        spill_panel["treatment_start_month"] = spill_panel["tract_geoid"].map(
            inherited_series
        )

        core: dict[str, Any]
        if not spillover_geoids or not pure_geoids:
            logger.warning(
                "Spillover CS skipped: need both spillover and pure_control tracts "
                "(have spillover=%d, pure_control=%d)",
                len(spillover_geoids),
                len(pure_geoids),
            )
            core = {
                "event_study": pd.DataFrame(),
                "overall_att": {
                    "att": float("nan"),
                    "se": float("nan"),
                    "ci_low": float("nan"),
                    "ci_high": float("nan"),
                    "p_value": float("nan"),
                },
                "cohort_info": {},
                "group_time_atts": pd.DataFrame(),
            }
        else:
            cs = CallawaySantAnnaAnalyzer(
                comparison_group=self.comparison_group,
                anticipation=self.anticipation,
                min_cohort_size=self.min_cohort_size,
            )
            core = cs.estimate_core_from_panel(spill_panel, log_cohort_summary=True)
            oa = core.get("overall_att") or {}
            if "p_value" not in oa:
                oa["p_value"] = float("nan")
                core["overall_att"] = oa

        results: dict[str, Any] = {
            "core": core,
            "classification": classification,
            "meta": meta,
            "spillover_panel_tracts": sorted(keep_geoids),
        }

        return {"cs_spillover_results": results}
