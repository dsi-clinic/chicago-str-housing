"""Descriptive analysis for DiD panel data.

This module provides descriptive statistics and balance checks for
Difference-in-Differences analysis of STR prohibition effects.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

SIGNIFICANCE_LEVEL = 0.05
# Align with CallawaySantAnnaAnalyzer(min_cohort_size=…) in DiD pipeline
MIN_COHORT_SIZE_FOR_DESCRIPTIONS = 5


class DIDDescriptiveAnalyzer(Analyzer):
    """Compute descriptive statistics for DiD analysis.

    This analyzer:
    1. Identifies ever-treated vs never-treated tracts
    2. Computes treatment adoption statistics
    3. Calculates average outcomes by group and time
    4. Performs pre-treatment balance checks
    5. Creates summary statistics tables
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DID descriptive analyzer.

        Args:
            output_dir: If set, write CSV summaries for slides / appendices here.
        """
        super().__init__(
            "did_descriptive_analysis",
            "Compute descriptive statistics and balance checks for DiD analysis",
        )
        self.required_data = ["did_panel"]
        self.output_dir = output_dir

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform descriptive analysis on the DiD panel.

        Required context keys:
            - did_panel: DataFrame with DiD panel data

        Returns:
            Dictionary with analysis results including:
            - did_panel: Updated panel with ever_treated indicator
            - adoption_by_month: Treatment adoption over time
            - avg_by_group_month: Average rental prices by group and month
            - pre_balance: Pre-treatment balance statistics
            - summary_stats: Overall summary statistics table
            - balance_test: T-test results for pre-treatment balance
        """
        did_panel = context["did_panel"].copy()

        logger.info("Running DiD descriptive analysis...")

        # Step 1: Identify ever-treated vs never-treated tracts
        did_panel = self._add_ever_treated(did_panel)

        # Step 2: Compute treatment adoption over time
        adoption_stats = self._compute_adoption_stats(did_panel)

        # Step 3: Average outcomes by group and month
        avg_by_group_month = self._compute_avg_by_group(did_panel)

        # Step 4: Pre-treatment balance check
        pre_balance, balance_test = self._check_pre_balance(did_panel)

        # Step 5: Summary statistics table
        summary_stats = self._compute_summary_stats(did_panel)

        # Step 6: Panel coverage (balanced vs unbalanced tract-month structure)
        panel_structure = self._compute_panel_structure(did_panel)

        # Step 7: Track how the tract sample shrinks across loaders/processors
        sample_lineage = self._compute_sample_lineage(context, did_panel)

        # Per-cohort descriptives (uses covariates when merged by DIDCovariateProcessor)
        panel_with_cov = context.get("did_panel_with_covariates")
        cohort_stats = self._compute_cohort_stats(
            panel_with_cov if panel_with_cov is not None else did_panel,
            min_cohort_size=MIN_COHORT_SIZE_FOR_DESCRIPTIONS,
        )

        if self.output_dir:
            self._export_tables(
                output_dir=self.output_dir,
                context=context,
                adoption_stats=adoption_stats,
                pre_balance=pre_balance,
                summary_stats=summary_stats,
                balance_test=balance_test,
                panel_structure=panel_structure,
                sample_lineage=sample_lineage,
                did_panel=did_panel,
                cohort_stats=cohort_stats,
            )

        # Log key findings
        self._log_findings(
            did_panel, adoption_stats, pre_balance, balance_test, panel_structure
        )

        return {
            "did_panel": did_panel,
            "adoption_by_month": adoption_stats["adoption_by_month"],
            "cumulative_adoption": adoption_stats["cumulative_adoption"],
            "avg_by_group_month": avg_by_group_month,
            "pre_balance": pre_balance,
            "summary_stats": summary_stats,
            "balance_test": balance_test,
            "first_treatment_date": adoption_stats["first_treatment_date"],
            "panel_structure": panel_structure,
            "sample_lineage": sample_lineage,
            "did_cohort_stats": cohort_stats,
        }

    def _add_ever_treated(self, panel: pd.DataFrame) -> pd.DataFrame:
        """Add ever_treated indicator to the panel.

        A tract is ever_treated if it receives treatment at any point in the sample.
        """
        ever_treated = panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        panel["ever_treated"] = (
            panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        return panel

    def _compute_adoption_stats(self, df: pd.DataFrame) -> dict[str, Any]:
        """Compute treatment adoption statistics over time."""
        # Number of treated tracts by month
        treated_tracts_by_month = (
            df[df["treated"] == 1]
            .groupby("month")["tract_geoid"]
            .nunique()
            .sort_index()
        )

        # Cumulative adoption (unique treated tracts up to each month)
        all_months = df["month"].sort_values().unique()
        cumulative = []

        for month in all_months:
            n_treated = df[(df["month"] <= month) & (df["treated"] == 1)][
                "tract_geoid"
            ].nunique()
            cumulative.append({"month": month, "cumulative_treated": n_treated})

        cumulative_df = pd.DataFrame(cumulative).set_index("month")

        # First treatment date
        first_treatment = df.loc[df["treated"] == 1, "month"].min()

        return {
            "adoption_by_month": treated_tracts_by_month,
            "cumulative_adoption": cumulative_df,
            "first_treatment_date": first_treatment,
        }

    def _compute_avg_by_group(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute average rental prices by ever_treated status and month."""
        avg_by_group = (
            df.groupby(["month", "ever_treated"])["rental_price"].mean().unstack()  # noqa: PD010
        )
        avg_by_group.columns = ["Never Treated", "Eventually Treated"]

        return avg_by_group

    def _check_pre_balance(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, dict[str, float]]:
        """Check pre-treatment balance between groups."""
        # Define pre-treatment period
        first_treatment = df.loc[df["treated"] == 1, "month"].min()
        pre_period = df[df["month"] < first_treatment]

        if len(pre_period) == 0:
            logger.warning("No pre-treatment observations found!")
            return pd.DataFrame(), {"t_stat": None, "p_value": None}

        # Compare average pre-treatment rental prices
        pre_balance = pre_period.groupby("ever_treated")["rental_price"].agg(
            ["mean", "std", "count"]
        )
        pre_balance.index = ["Never Treated", "Eventually Treated"]
        pre_balance.columns = ["Mean Rent", "Std Dev", "N Observations"]

        # T-test for difference in means
        never_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 0, "rental_price"
        ]
        eventually_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]

        if len(never_treated_prices) > 0 and len(eventually_treated_prices) > 0:
            t_stat, p_value = stats.ttest_ind(
                never_treated_prices, eventually_treated_prices
            )
            balance_test = {"t_stat": t_stat, "p_value": p_value}
        else:
            balance_test = {"t_stat": None, "p_value": None}

        return pre_balance, balance_test

    def _compute_summary_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute overall summary statistics by treatment group."""
        summary = df.groupby("ever_treated").agg(
            {
                "tract_geoid": "nunique",
                "rental_price": ["mean", "std", "min", "max"],
                "treated": "sum",
            }
        )

        # Flatten column names
        summary.columns = [
            "N Tracts",
            "Mean Rent",
            "Std Dev",
            "Min Rent",
            "Max Rent",
            "Treated Obs",
        ]
        summary.index = ["Never Treated", "Eventually Treated"]

        return summary

    def _compute_panel_structure(self, df: pd.DataFrame) -> dict[str, Any]:
        """Summarize tract--time coverage (how 'balanced' the panel is)."""
        n_tracts = df["tract_geoid"].nunique()
        n_periods = df["month"].nunique()
        total_cells = n_tracts * n_periods
        n_obs = len(df)
        n_nonmiss = df["rental_price"].notna().sum()
        miss_share = 1.0 - (n_nonmiss / n_obs) if n_obs else 0.0

        months_per_tract = df.groupby("tract_geoid")["month"].nunique()
        counts_per_tract = df.groupby("tract_geoid")["rental_price"].apply(
            lambda s: int(s.notna().sum())
        )
        full_span_tracts = int((months_per_tract == n_periods).sum())

        by_group = df.groupby("ever_treated")["tract_geoid"].nunique()
        n_never = int(by_group.get(0, 0))
        n_event = int(by_group.get(1, 0))

        return {
            "n_tracts": n_tracts,
            "n_periods": n_periods,
            "n_observations": n_obs,
            "share_missing_rental_price": float(miss_share),
            "tracts_with_full_month_span": full_span_tracts,
            "share_tracts_full_span": float(full_span_tracts / n_tracts)
            if n_tracts
            else 0.0,
            "tract_months_min": int(counts_per_tract.min())
            if len(counts_per_tract)
            else 0,
            "tract_months_median": float(counts_per_tract.median())
            if len(counts_per_tract)
            else 0.0,
            "tract_months_max": int(counts_per_tract.max())
            if len(counts_per_tract)
            else 0,
            "notional_balanced_cells": total_cells,
            "tracts_never_treated": n_never,
            "tracts_eventually_treated": n_event,
        }

    def _compute_sample_lineage(
        self,
        context: dict[str, Any],
        matched_panel: pd.DataFrame,
    ) -> pd.DataFrame:
        """Summarize tract counts from city boundaries to the final analysis sample."""
        rows: list[dict[str, Any]] = []

        tract_boundaries = context.get("tract_boundaries")
        n_city_tracts = (
            int(tract_boundaries["tract_geoid"].nunique())
            if tract_boundaries is not None and "tract_geoid" in tract_boundaries
            else None
        )

        def _pct_city(n_tracts: int | None) -> float | None:
            if n_city_tracts in (None, 0) or n_tracts is None:
                return None
            return round(n_tracts / n_city_tracts, 4)

        def _delta(current: int | None, previous: int | None) -> int | None:
            if current is None or previous is None:
                return None
            return int(current - previous)

        prev_n: int | None = None

        def _append_row(
            stage_code: str,
            stage_label: str,
            n_tracts: int | None,
            reason: str,
            treated_tracts: int | None = None,
            never_treated_tracts: int | None = None,
            extra: dict[str, Any] | None = None,
            counts_as_filter_step: bool = True,
        ) -> None:
            nonlocal prev_n
            row = {
                "stage_code": stage_code,
                "stage_label": stage_label,
                "n_tracts": n_tracts,
                "share_of_city_tracts": _pct_city(n_tracts),
                "delta_from_previous_stage": (
                    _delta(n_tracts, prev_n) if counts_as_filter_step else None
                ),
                "treated_tracts": treated_tracts,
                "never_treated_tracts": never_treated_tracts,
                "reason": reason,
            }
            if extra:
                row.update(extra)
            rows.append(row)
            if counts_as_filter_step:
                prev_n = n_tracts

        _append_row(
            "A",
            "Chicago tract boundaries",
            n_city_tracts,
            "All census tracts loaded from the shapefile after the Chicago/Cook County study-area filter.",
        )

        zip_tract_crosswalk = context.get("zip_to_tract_crosswalk")
        n_crosswalk_tracts = (
            int(zip_tract_crosswalk["tract_geoid"].nunique())
            if zip_tract_crosswalk is not None and "tract_geoid" in zip_tract_crosswalk
            else None
        )
        _append_row(
            "B",
            "ZIP-tract crosswalk coverage",
            n_crosswalk_tracts,
            "Tracts that intersect at least one Chicago ZIP boundary in the geometric crosswalk.",
        )

        tract_panel_data = context.get("tract_panel_data")
        n_rent_panel_tracts = (
            int(tract_panel_data["tract_geoid"].nunique())
            if tract_panel_data is not None and "tract_geoid" in tract_panel_data
            else None
        )
        months_in_panel = (
            int(tract_panel_data["month"].nunique())
            if tract_panel_data is not None and "month" in tract_panel_data
            else None
        )
        _append_row(
            "C",
            "Rent panel coverage",
            n_rent_panel_tracts,
            "Tracts with observed ZORI rent history after applying ZIP-to-tract weights.",
            extra={"n_months": months_in_panel},
        )

        census_data = context.get("census_data")
        n_acs_tracts_total = (
            int(census_data["tract_id"].nunique())
            if census_data is not None and "tract_id" in census_data
            else None
        )
        rent_panel_tracts_with_acs = None
        if census_data is not None and tract_panel_data is not None:
            census_ids = set(census_data["tract_id"].astype(str))
            panel_ids = set(tract_panel_data["tract_geoid"].astype(str))
            rent_panel_tracts_with_acs = int(len(panel_ids & census_ids))

        raw_did_panel = context.get("did_panel_unmatched")
        if raw_did_panel is not None and "tract_geoid" in raw_did_panel:
            ever_treated_raw = raw_did_panel.groupby("tract_geoid")["treated"].max()
            n_raw = int(ever_treated_raw.index.nunique())
            n_raw_treated = int((ever_treated_raw >= 1).sum())
            n_raw_never = int(n_raw - n_raw_treated)
        else:
            n_raw = None
            n_raw_treated = None
            n_raw_never = None
        _append_row(
            "D",
            "Pre-match DiD panel",
            n_raw,
            "Treatment split under the current treatment definition before trend matching.",
            treated_tracts=n_raw_treated,
            never_treated_tracts=n_raw_never,
        )

        _append_row(
            "E",
            "ACS coverage within rent panel",
            rent_panel_tracts_with_acs,
            "Coverage note only: these tracts have ACS covariates and occupied-unit denominators available after Census cleaning. Tracts missing ACS can still remain in the matched sample, but their controls are less complete.",
            extra={"acs_tracts_total": n_acs_tracts_total},
            counts_as_filter_step=False,
        )

        ever_treated_matched = matched_panel.groupby("tract_geoid")["treated"].max()
        n_matched = int(ever_treated_matched.index.nunique())
        n_matched_treated = int((ever_treated_matched >= 1).sum())
        n_matched_never = int(n_matched - n_matched_treated)
        _append_row(
            "F",
            "Matched DiD panel",
            n_matched,
            "Tracts retained after k=3 nearest-neighbor matching on standardized pre-treatment slope and average pre-treatment rent, with at least 6 pre-treatment months.",
            treated_tracts=n_matched_treated,
            never_treated_tracts=n_matched_never,
        )

        cohort_stats = self._compute_cohort_stats(
            context.get("did_panel_with_covariates", matched_panel),
            min_cohort_size=MIN_COHORT_SIZE_FOR_DESCRIPTIONS,
        )
        if cohort_stats is not None and not cohort_stats.empty:
            n_cs_treated = int(cohort_stats["n_tracts"].sum())
            n_cs_cohorts = int(len(cohort_stats))
            _append_row(
                "G",
                "CS-visible treated cohorts",
                n_cs_treated,
                "Treated tracts that remain in cohort-level CS figures/tables after dropping adoption months with fewer than 5 treated tracts.",
                treated_tracts=n_cs_treated,
                never_treated_tracts=0,
                extra={"n_cs_cohort_months": n_cs_cohorts},
            )

        return pd.DataFrame(rows)

    def _compute_cohort_stats(
        self,
        panel: pd.DataFrame,
        min_cohort_size: int,
    ) -> pd.DataFrame:
        """One row per first-prohibition cohort (sizes >= ``min_cohort_size``).

        Mirrors Callaway-Sant'Anna cohort dropping of small cohorts for deck tables.
        """
        if panel is None or len(panel) == 0:
            return pd.DataFrame()

        tract_first = (
            panel[panel["treated"] == 1]
            .groupby("tract_geoid")["month"]
            .min()
            .reset_index()
            .rename(columns={"month": "first_prohibition_month"})
        )
        if tract_first.empty:
            return pd.DataFrame()

        n_treated_matched = int(
            panel.groupby("tract_geoid")["treated"].max().astype(int).sum()
        )
        tract_first_full = tract_first.copy()
        sizes = tract_first_full.groupby("first_prohibition_month").size()
        kept_cohorts = sizes[sizes >= min_cohort_size].index
        tract_kept = tract_first_full[
            tract_first_full["first_prohibition_month"].isin(kept_cohorts)
        ]

        # One tract-level covariate row per tract (time-invariant)
        tract_one = (
            panel.sort_values(["tract_geoid", "month"])
            .drop_duplicates(subset=["tract_geoid"], keep="first")
            .merge(tract_kept, on="tract_geoid", how="inner")
        )

        rows: list[dict[str, Any]] = []
        for cohort_month in sorted(tract_kept["first_prohibition_month"].unique()):
            sub = tract_one[tract_one["first_prohibition_month"] == cohort_month].copy()
            n_c = len(sub)
            row: dict[str, Any] = {
                "first_prohibition_month": pd.Timestamp(cohort_month).strftime(
                    "%Y-%m-%d"
                ),
                "n_tracts": int(n_c),
                "share_of_treated_tracts": round(n_c / n_treated_matched, 4)
                if n_treated_matched
                else float("nan"),
            }
            for col in (
                "baseline_rent",
                "median_income",
                "pct_bachelor",
                "pct_rented",
            ):
                if col in sub.columns and sub[col].notna().any():
                    row[f"mean_{col}"] = float(sub[col].mean(skipna=True))
                else:
                    row[f"mean_{col}"] = float("nan")
            rows.append(row)

        cohort_df = pd.DataFrame(rows)
        if cohort_df.empty:
            return cohort_df
        cohort_df["first_prohibition_month"] = cohort_df[
            "first_prohibition_month"
        ].astype(str)
        cohort_df.attrs["min_cohort_size"] = min_cohort_size
        return cohort_df

    def _export_tables(
        self,
        output_dir: str,
        context: dict[str, Any],
        adoption_stats: dict[str, Any],
        pre_balance: pd.DataFrame,
        summary_stats: pd.DataFrame,
        balance_test: dict[str, float],
        panel_structure: dict[str, Any],
        sample_lineage: pd.DataFrame,
        did_panel: pd.DataFrame,
        cohort_stats: pd.DataFrame | None,
    ) -> None:
        """Write CSV tables for appendices, Beamer tables, and QA."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        summary_stats.to_csv(out / "did_descriptive_summary_stats.csv")
        if len(pre_balance) > 0:
            pre_balance.to_csv(out / "did_descriptive_pre_balance.csv")

        pd.DataFrame([balance_test]).to_csv(
            out / "did_descriptive_balance_test.csv", index=False
        )
        pd.DataFrame([panel_structure]).to_csv(
            out / "did_descriptive_panel_overview.csv", index=False
        )
        if sample_lineage is not None and not sample_lineage.empty:
            sample_lineage.to_csv(
                out / "did_descriptive_sample_lineage.csv", index=False
            )

        crosswalk_diagnostics = context.get("crosswalk_diagnostics")
        if crosswalk_diagnostics:
            pd.DataFrame([crosswalk_diagnostics]).drop(
                columns=["projected_crs"], errors="ignore"
            ).to_csv(out / "did_crosswalk_diagnostics.csv", index=False)

        crosswalk_coverage = context.get("crosswalk_tract_coverage")
        if crosswalk_coverage is not None and not crosswalk_coverage.empty:
            crosswalk_coverage.to_csv(
                out / "did_crosswalk_tract_coverage.csv", index=False
            )

        matching_diagnostics = context.get("matching_diagnostics")
        if matching_diagnostics:
            matching_row = {
                k: v
                for k, v in matching_diagnostics.items()
                if k != "control_reuse_table"
            }
            pd.DataFrame([matching_row]).to_csv(
                out / "did_matching_diagnostics.csv", index=False
            )
            control_reuse = matching_diagnostics.get("control_reuse_table")
            if control_reuse is not None and not control_reuse.empty:
                control_reuse.to_csv(
                    out / "did_matching_control_reuse.csv", index=False
                )

        adoption_stats["adoption_by_month"].to_csv(
            out / "did_descriptive_adoption_by_month.csv"
        )
        adoption_stats["cumulative_adoption"].to_csv(
            out / "did_descriptive_cumulative_adoption.csv"
        )

        tract_cov = (
            did_panel.groupby(["tract_geoid", "ever_treated"])
            .agg(
                n_obs=("rental_price", lambda s: int(s.notna().sum())),
                n_months=("month", "nunique"),
                first_month=("month", "min"),
                last_month=("month", "max"),
            )
            .reset_index()
        )
        tract_cov.to_csv(out / "did_descriptive_tract_coverage.csv", index=False)

        if cohort_stats is not None and not cohort_stats.empty:
            cohort_stats.to_csv(out / "did_descriptive_cohort_stats.csv", index=False)
            logger.info(
                "Wrote cohort descriptive table (%d rows)",
                len(cohort_stats),
            )

        logger.info("Wrote DiD descriptive tables to %s", out)

    def _log_findings(
        self,
        df: pd.DataFrame,
        adoption_stats: dict[str, Any],
        pre_balance: pd.DataFrame,
        balance_test: dict[str, float],
        panel_structure: dict[str, Any],
    ) -> None:
        """Log key findings from the descriptive analysis."""
        logger.info("\n" + "=" * 60)
        logger.info("DiD Descriptive Analysis Results")
        logger.info("=" * 60)

        # Treatment groups
        n_tracts = df["tract_geoid"].nunique()
        n_ever_treated = df[df["ever_treated"] == 1]["tract_geoid"].nunique()
        n_never_treated = n_tracts - n_ever_treated

        logger.info("\nTreatment Groups:")
        logger.info("  Total tracts: %d", n_tracts)
        logger.info(
            "  Ever treated: %d (%.1f%%)",
            n_ever_treated,
            100 * n_ever_treated / n_tracts,
        )
        logger.info(
            "  Never treated: %d (%.1f%%)",
            n_never_treated,
            100 * n_never_treated / n_tracts,
        )

        # Treatment timing
        first_treatment = adoption_stats["first_treatment_date"]
        logger.info("\nTreatment Timing:")
        logger.info("  First treatment: %s", first_treatment.strftime("%Y-%m"))

        # Pre-treatment balance
        if len(pre_balance) > 0:
            logger.info("\nPre-Treatment Balance:")
            for group in pre_balance.index:
                mean_rent = pre_balance.loc[group, "Mean Rent"]
                logger.info("  %s: $%.0f average rent", group, mean_rent)

            if balance_test["t_stat"] is not None:
                logger.info("\nBalance Test (t-test):")
                logger.info("  t-statistic: %.2f", balance_test["t_stat"])
                logger.info("  p-value: %.4f", balance_test["p_value"])

                if balance_test["p_value"] < SIGNIFICANCE_LEVEL:
                    logger.warning(
                        "  Groups have statistically different pre-treatment rents (p < 0.05)"
                    )
                else:
                    logger.info(
                        "  No significant difference in pre-treatment rents (p >= 0.05)"
                    )

        logger.info("\nPanel structure:")
        logger.info("  Periods (distinct months): %d", panel_structure["n_periods"])
        logger.info(
            "  Tracts with observations in all %d months: %d (%.1f%%)",
            panel_structure["n_periods"],
            panel_structure["tracts_with_full_month_span"],
            100 * panel_structure["share_tracts_full_span"],
        )
        logger.info(
            "  Obs per tract (non-missing rent): min %s, median %.1f, max %s",
            panel_structure["tract_months_min"],
            panel_structure["tract_months_median"],
            panel_structure["tract_months_max"],
        )
        logger.info(
            "  Share of tract-months missing rent: %.2f%%",
            100 * panel_structure["share_missing_rental_price"],
        )
