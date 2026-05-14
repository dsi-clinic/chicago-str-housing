"""Callaway & Sant'Anna subgroup heterogeneity (baseline CS, no covariate adjustment).

Splits treated tracts by ACS neighborhood characteristics, prohibition intensity,
or pre-policy STR proxy (tract Airbnb listing density from a listings snapshot),
keeps **all never-treated tracts** as the comparison group for each subgroup, and
re-estimates CS via :meth:`CallawaySantAnnaAnalyzer.estimate_core_from_panel`.

Also compares **early vs. late** adopters by median first-treatment calendar month.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.processors.did_covariate_merger import DIDCovariateProcessor
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

# Need at least two treated tracts with the moderator to form low/high median split.
_MIN_TRACTS_FOR_MEDIAN_SPLIT = 2


def _never_treated_tract_geoids(panel: pd.DataFrame) -> list[Any]:
    """Tracts with no treated==1 in the panel."""
    ever = panel.groupby("tract_geoid", observed=True)["treated"].max()
    return ever[ever == 0].index.tolist()


def _treated_tract_geoids(panel: pd.DataFrame) -> list[Any]:
    """Tracts with at least one treated==1."""
    ever = panel.groupby("tract_geoid", observed=True)["treated"].max()
    return ever[ever == 1].index.tolist()


def _first_treatment_month(panel: pd.DataFrame) -> pd.Series:
    """Per-tract first calendar month with treated==1."""
    t = panel.loc[panel["treated"] == 1, ["tract_geoid", "month"]]
    return t.groupby("tract_geoid", observed=True)["month"].min()


def _tract_census_frame(
    panel: pd.DataFrame, census: pd.DataFrame | None
) -> pd.DataFrame:
    """One row per tract with ACS columns merged (county-median imputation)."""
    keys = panel[["tract_geoid"]].drop_duplicates().reset_index(drop=True)
    if census is None or census.empty:
        logger.warning("No census_data in context; heterogeneity splits need ACS.")
        return keys
    merger = DIDCovariateProcessor()
    return merger._merge_census_data(keys, census)  # noqa: SLF001


def _tract_airbnb_density_frame(
    panel: pd.DataFrame, airbnb_tract: object
) -> pd.DataFrame:
    """One row per panel tract with ``airbnb_density`` when available."""
    keys = panel[["tract_geoid"]].drop_duplicates().reset_index(drop=True)
    if airbnb_tract is None:
        logger.warning("No airbnb_tract_data; skip airbnb_density heterogeneity.")
        return keys
    raw = airbnb_tract
    if hasattr(raw, "drop_geometry"):
        airbnb_tbl = pd.DataFrame(raw.drop_geometry())
    else:
        airbnb_tbl = pd.DataFrame(raw)
    if (
        "tract_geoid" not in airbnb_tbl.columns
        or "airbnb_density" not in airbnb_tbl.columns
    ):
        logger.warning(
            "airbnb_tract_data missing tract_geoid or airbnb_density; skip airbnb split."
        )
        return keys
    sub = airbnb_tbl[["tract_geoid", "airbnb_density"]].drop_duplicates(
        subset=["tract_geoid"]
    )
    return keys.merge(sub, on="tract_geoid", how="left")


def _peak_pct_restricted(panel: pd.DataFrame) -> pd.Series:
    """Max pct_units_restricted per tract over the panel window."""
    return panel.groupby("tract_geoid", observed=True)["pct_units_restricted"].max()


def _subset_panel_for_subgroup(
    panel: pd.DataFrame,
    subgroup_treated_geoids: list[Any],
    never_treated_geoids: list[Any],
) -> pd.DataFrame:
    keep = set(subgroup_treated_geoids) | set(never_treated_geoids)
    return panel[panel["tract_geoid"].isin(keep)].copy()


def _run_cs_on_panel(
    panel: pd.DataFrame,
    *,
    comparison_group: str,
    anticipation: int,
    min_cohort_size: int,
    log_cohort_summary: bool,
) -> dict[str, Any]:
    cs = CallawaySantAnnaAnalyzer(
        comparison_group=comparison_group,
        anticipation=anticipation,
        min_cohort_size=min_cohort_size,
    )
    return cs.estimate_core_from_panel(panel, log_cohort_summary=log_cohort_summary)


def _summarize_core(
    core: dict[str, Any],
    *,
    split: str,
    subgroup: str,
) -> dict[str, Any]:
    """Flatten overall ATT + cohort counts for CSV export."""
    oa = core.get("overall_att") or {}
    cohort_info = core.get("cohort_info") or {}
    treated_df = cohort_info.get("treated_cohorts")
    n_treated = 0
    if isinstance(treated_df, pd.DataFrame) and not treated_df.empty:
        n_treated = int(treated_df["tract_geoid"].nunique())
    n_never = int(cohort_info.get("n_never_treated", 0) or 0)
    es = core.get("event_study")
    n_rel = len(es) if isinstance(es, pd.DataFrame) else 0
    return {
        "split": split,
        "subgroup": subgroup,
        "att": float(oa.get("att", float("nan"))),
        "se": float(oa.get("se", float("nan"))),
        "ci_low": float(oa.get("ci_low", float("nan"))),
        "ci_high": float(oa.get("ci_high", float("nan"))),
        "p_value": float(oa.get("p_value", float("nan"))),
        "n_treated_tracts": n_treated,
        "n_never_treated_tracts": n_never,
        "n_event_study_periods": n_rel,
    }


class CallawaySantAnnaHeterogeneityAnalyzer(Analyzer):
    """Subgroup CS heterogeneity on the matched DID panel."""

    def __init__(
        self,
        comparison_group: str = "nevertreated",
        anticipation: int = 0,
        min_cohort_size: int = 5,
    ) -> None:
        """Configure CS subgroup runs (same knobs as :class:`CallawaySantAnnaAnalyzer`)."""
        super().__init__(
            "callaway_santanna_heterogeneity_analysis",
            "Callaway & Sant'Anna heterogeneity by neighborhood / dose / STR density",
        )
        self.comparison_group = comparison_group
        self.anticipation = anticipation
        self.min_cohort_size = min_cohort_size

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Estimate CS on median splits; write ``cs_heterogeneity_results`` to context."""
        did_panel = context.get("did_panel")
        if did_panel is None or did_panel.empty:
            raise ValueError("did_panel not found or empty")

        panel = did_panel.copy()
        census = context.get("census_data")

        never_tr = _never_treated_tract_geoids(panel)
        treated_tr = _treated_tract_geoids(panel)
        logger.info(
            "Heterogeneity: %d treated tracts, %d never-treated (comparison pool)",
            len(treated_tr),
            len(never_tr),
        )

        tract_acs = _tract_census_frame(panel, census)
        tract_acs = tract_acs.drop_duplicates(subset=["tract_geoid"]).set_index(
            "tract_geoid", drop=True
        )

        splits_out: dict[str, Any] = {}
        summary_rows: list[dict[str, Any]] = []
        meta: dict[str, Any] = {}

        # --- income (median among treated) ---
        if "median_income" in tract_acs.columns:
            inc = tract_acs.loc[
                tract_acs.index.isin(treated_tr), "median_income"
            ].dropna()
            if len(inc) >= _MIN_TRACTS_FOR_MEDIAN_SPLIT:
                med_inc = float(inc.median())
                meta["median_income_cutoff"] = med_inc
                high_tr = inc[inc > med_inc].index.tolist()
                low_tr = inc[inc <= med_inc].index.tolist()
                splits_out["income"] = self._two_subgroup_estimate(
                    panel,
                    low_tr,
                    high_tr,
                    never_tr,
                    "income",
                    summary_rows,
                )
            else:
                logger.warning(
                    "Too few treated tracts with median_income; skip income."
                )
        else:
            logger.warning("median_income missing after census merge; skip income.")

        # --- renter share ---
        if "pct_rented" in tract_acs.columns:
            pr = tract_acs.loc[tract_acs.index.isin(treated_tr), "pct_rented"].dropna()
            if len(pr) >= _MIN_TRACTS_FOR_MEDIAN_SPLIT:
                med_pr = float(pr.median())
                meta["median_pct_rented_cutoff"] = med_pr
                high_tr = pr[pr > med_pr].index.tolist()
                low_tr = pr[pr <= med_pr].index.tolist()
                splits_out["renter_share"] = self._two_subgroup_estimate(
                    panel,
                    low_tr,
                    high_tr,
                    never_tr,
                    "renter_share",
                    summary_rows,
                )
            else:
                logger.warning("Too few treated tracts with pct_rented; skip renter.")
        else:
            logger.warning("pct_rented missing; skip renter_share.")

        # --- Airbnb listing density (proxy for pre-prohibition STR intensity) ---
        tract_airbnb = _tract_airbnb_density_frame(
            panel, context.get("airbnb_tract_data")
        )
        tract_airbnb = tract_airbnb.drop_duplicates(subset=["tract_geoid"]).set_index(
            "tract_geoid", drop=True
        )
        if "airbnb_density" in tract_airbnb.columns:
            ad = tract_airbnb.loc[
                tract_airbnb.index.isin(treated_tr), "airbnb_density"
            ].dropna()
            if len(ad) >= _MIN_TRACTS_FOR_MEDIAN_SPLIT:
                med_ad = float(ad.median())
                meta["median_airbnb_density_cutoff"] = med_ad
                high_tr = ad[ad > med_ad].index.tolist()
                low_tr = ad[ad <= med_ad].index.tolist()
                splits_out["airbnb_density"] = self._two_subgroup_estimate(
                    panel,
                    low_tr,
                    high_tr,
                    never_tr,
                    "airbnb_density",
                    summary_rows,
                )
            else:
                logger.warning(
                    "Too few treated tracts with airbnb_density; skip airbnb_density."
                )
        else:
            logger.warning("airbnb_density missing; skip airbnb_density split.")

        # --- dose: peak pct_units_restricted among treated ---
        peak = _peak_pct_restricted(panel)
        peak_t = peak.reindex(treated_tr).dropna()
        if len(peak_t) >= _MIN_TRACTS_FOR_MEDIAN_SPLIT:
            med_d = float(peak_t.median())
            meta["median_peak_pct_restricted_cutoff"] = med_d
            high_tr = peak_t[peak_t > med_d].index.tolist()
            low_tr = peak_t[peak_t <= med_d].index.tolist()
            splits_out["dose"] = self._two_subgroup_estimate(
                panel,
                low_tr,
                high_tr,
                never_tr,
                "dose",
                summary_rows,
            )
        else:
            logger.warning("Too few treated tracts for dose split; skip dose.")

        # --- early vs late (median first treatment month among treated) ---
        ft = _first_treatment_month(panel).reindex(treated_tr).dropna()
        if len(ft) >= _MIN_TRACTS_FOR_MEDIAN_SPLIT:
            med_dt = pd.Timestamp(ft.median())
            meta["median_first_treatment_month"] = med_dt.isoformat()
            early_tr = ft[ft <= med_dt].index.tolist()
            late_tr = ft[ft > med_dt].index.tolist()
            splits_out["cohort_timing"] = self._two_subgroup_estimate(
                panel,
                early_tr,
                late_tr,
                never_tr,
                "cohort_timing",
                summary_rows,
                labels=("early", "late"),
            )
        else:
            logger.warning("Too few treated tracts for cohort timing; skip.")

        summary_cols = [
            "split",
            "subgroup",
            "att",
            "se",
            "ci_low",
            "ci_high",
            "p_value",
            "n_treated_tracts",
            "n_never_treated_tracts",
            "n_event_study_periods",
        ]
        summary_table = (
            pd.DataFrame(summary_rows)
            if summary_rows
            else pd.DataFrame(columns=summary_cols)
        )

        results: dict[str, Any] = {
            "splits": splits_out,
            "meta": meta,
            "summary_table": summary_table,
        }

        return {"cs_heterogeneity_results": results}

    def _two_subgroup_estimate(
        self,
        panel: pd.DataFrame,
        low_tr: list[Any],
        high_tr: list[Any],
        never_tr: list[Any],
        split_name: str,
        summary_rows: list[dict[str, Any]],
        *,
        labels: tuple[str, str] = ("low", "high"),
    ) -> dict[str, Any]:
        out: dict[str, Any] = {}
        label_a, label_b = labels

        for label, tr_list in ((label_a, low_tr), (label_b, high_tr)):
            if not tr_list:
                logger.warning(
                    "Empty treated set for split=%s subgroup=%s",
                    split_name,
                    label,
                )
                out[label] = {
                    "event_study": pd.DataFrame(),
                    "overall_att": {},
                    "cohort_info": {},
                    "group_time_atts": pd.DataFrame(),
                }
                summary_rows.append(
                    _summarize_core(
                        {
                            "overall_att": {},
                            "cohort_info": {},
                            "event_study": pd.DataFrame(),
                        },
                        split=split_name,
                        subgroup=label,
                    )
                )
                continue

            sub = _subset_panel_for_subgroup(panel, tr_list, never_tr)
            core = _run_cs_on_panel(
                sub,
                comparison_group=self.comparison_group,
                anticipation=self.anticipation,
                min_cohort_size=self.min_cohort_size,
                log_cohort_summary=False,
            )
            out[label] = {
                "event_study": core["event_study"],
                "overall_att": core["overall_att"],
                "cohort_info": core["cohort_info"],
                "group_time_atts": core["group_time_atts"],
            }
            summary_rows.append(_summarize_core(core, split=split_name, subgroup=label))
            logger.info(
                "CS heterogeneity %s / %s: ATT=%.2f SE=%.2f (n_treated=%d)",
                split_name,
                label,
                float((core.get("overall_att") or {}).get("att", float("nan"))),
                float((core.get("overall_att") or {}).get("se", float("nan"))),
                int(core["cohort_info"]["treated_cohorts"]["tract_geoid"].nunique())
                if isinstance(core["cohort_info"].get("treated_cohorts"), pd.DataFrame)
                and not core["cohort_info"]["treated_cohorts"].empty
                else 0,
            )

        return out
