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

        if self.output_dir:
            self._export_tables(
                output_dir=self.output_dir,
                adoption_stats=adoption_stats,
                pre_balance=pre_balance,
                summary_stats=summary_stats,
                balance_test=balance_test,
                panel_structure=panel_structure,
                did_panel=did_panel,
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
            "share_tracts_full_span": float(full_span_tracts / n_tracts) if n_tracts else 0.0,
            "tract_months_min": int(counts_per_tract.min()) if len(counts_per_tract) else 0,
            "tract_months_median": float(counts_per_tract.median()) if len(counts_per_tract) else 0.0,
            "tract_months_max": int(counts_per_tract.max()) if len(counts_per_tract) else 0,
            "notional_balanced_cells": total_cells,
            "tracts_never_treated": n_never,
            "tracts_eventually_treated": n_event,
        }

    def _export_tables(
        self,
        output_dir: str,
        adoption_stats: dict[str, Any],
        pre_balance: pd.DataFrame,
        summary_stats: pd.DataFrame,
        balance_test: dict[str, float],
        panel_structure: dict[str, Any],
        did_panel: pd.DataFrame,
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
        logger.info(
            "  Periods (distinct months): %d", panel_structure["n_periods"]
        )
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
