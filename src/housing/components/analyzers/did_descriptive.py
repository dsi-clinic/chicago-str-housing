"""Descriptive analysis for DiD panel data.

This module provides descriptive statistics and balance checks for
Difference-in-Differences analysis of STR prohibition effects.

This module performs descriptive analysis on DiD panel data, including:
- Counts of treated vs. never-treated tracts
- Average rental prices by group and month
- Pre-treatment balance statistics
- Summary statistics table
"""

import logging
from typing import Any

import pandas as pd
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDDescriptiveAnalyzer(Analyzer):
    """Compute descriptive statistics for DiD analysis.

    This analyzer:
    1. Identifies ever-treated vs never-treated tracts
    2. Computes treatment adoption statistics
    3. Calculates average outcomes by group and time
    4. Performs pre-treatment balance checks
    5. Creates summary statistics tables
    """

    def __init__(self) -> None:
        """Initialize the DID descriptive analyzer."""
        super().__init__(
            "did_descriptive_analysis",
<<<<<<< HEAD
            "Compute descriptive statistics and balance checks for DiD analysis",
=======
            "Perform descriptive analysis for difference-in-differences",
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)
        )
        self.required_data = ["did_panel"]

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
<<<<<<< HEAD
        did_panel = context["did_panel"].copy()

        logger.info("Running DiD descriptive analysis...")
=======
        did_panel = context["did_panel"]
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)

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

        # Log key findings
        self._log_findings(did_panel, adoption_stats, pre_balance, balance_test)

        return {
            "did_panel": did_panel,
            "adoption_by_month": adoption_stats["adoption_by_month"],
            "cumulative_adoption": adoption_stats["cumulative_adoption"],
            "avg_by_group_month": avg_by_group_month,
            "pre_balance": pre_balance,
            "summary_stats": summary_stats,
            "balance_test": balance_test,
            "first_treatment_date": adoption_stats["first_treatment_date"],
        }

    def _add_ever_treated(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ever_treated indicator to the panel.

        A tract is ever_treated if it receives treatment at any point in the sample.
        """
        ever_treated = df.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

<<<<<<< HEAD
        df["ever_treated"] = df["tract_geoid"].isin(ever_treated_tracts).astype(int)
=======
        did_panel["ever_treated"] = (
            did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)

        return df

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

<<<<<<< HEAD
    def _compute_avg_by_group(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute average rental prices by ever_treated status and month."""
        avg_by_group = df.pivot_table(
            index="month", columns="ever_treated", values="rental_price", aggfunc="mean"
=======
    def _count_tracts(self, did_panel: pd.DataFrame) -> dict[str, int]:
        """Count treated vs. never-treated tracts.

        Args:
            did_panel: DiD panel DataFrame

        Returns:
            Dictionary with counts
        """
        # Count unique tracts by ever_treated status
        tract_counts_by_status = did_panel.groupby("tract_geoid")[
            "ever_treated"
        ].first()

        treated_tracts = (tract_counts_by_status == 1).sum()
        never_treated_tracts = (tract_counts_by_status == 0).sum()
        total_tracts = len(tract_counts_by_status)

        return {
            "treated_tracts": int(treated_tracts),
            "never_treated_tracts": int(never_treated_tracts),
            "total_tracts": int(total_tracts),
        }

    def _compute_avg_rent_by_group_month(self, did_panel: pd.DataFrame) -> pd.DataFrame:
        """Compute average rental prices by group and month.

        Args:
            did_panel: DiD panel DataFrame

        Returns:
            DataFrame with month as index and columns: Never Treated, Eventually Treated
        """
        # Average rental price by ever_treated status and month
        avg_by_group = (
            did_panel.groupby(["month", "ever_treated"])["rental_price"]
            .mean()
            .unstack()
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)
        )
        avg_by_group.columns = ["Never Treated", "Eventually Treated"]

        return avg_by_group

<<<<<<< HEAD
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
=======
    def _compute_pre_treatment_balance(self, did_panel: pd.DataFrame) -> pd.DataFrame:
        """Compute pre-treatment balance statistics.

        Compares treated and control groups before any treatment occurs.

        Args:
            did_panel: DiD panel DataFrame

        Returns:
            DataFrame with pre-treatment balance statistics by group
        """
        # Define pre-treatment period (before any tract is treated)
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
        pre_period = did_panel[did_panel["month"] < first_treatment]
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)

        # Compare average pre-treatment rental prices
        pre_balance = pre_period.groupby("ever_treated")["rental_price"].agg(
            ["mean", "std", "count"]
        )
        pre_balance.index = ["Never Treated", "Eventually Treated"]
        pre_balance.columns = ["Mean Rent", "Std Dev", "N Observations"]

<<<<<<< HEAD
        # T-test for difference in means
=======
        # Perform t-test to compare groups
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)
        never_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 0, "rental_price"
        ]
        eventually_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]

<<<<<<< HEAD
        if len(never_treated_prices) > 0 and len(eventually_treated_prices) > 0:
            t_stat, p_value = stats.ttest_ind(
                never_treated_prices, eventually_treated_prices
            )
            balance_test = {"t_stat": t_stat, "p_value": p_value}
        else:
            balance_test = {"t_stat": None, "p_value": None}
=======
        t_stat, p_value = stats.ttest_ind(
            never_treated_prices, eventually_treated_prices
        )
        logger.info("  t-statistic: %.2f, p-value: %.4f", t_stat, p_value)
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)

        return pre_balance, balance_test

<<<<<<< HEAD
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
=======
    def _create_summary_stats_table(self, did_panel: pd.DataFrame) -> pd.DataFrame:
        """Create summary statistics table.

        Args:
            did_panel: DiD panel DataFrame

        Returns:
            DataFrame with summary statistics by group
        """
        summary = did_panel.groupby("ever_treated").agg(
            {
                "tract_geoid": "nunique",
                "rental_price": ["mean", "std", "min", "max"],
                "treated": "sum",  # Total treated tract-months
            }
        )

        # Flatten MultiIndex columns
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)
        summary.columns = [
            "N Tracts",
            "Mean Rent",
            "Std Dev",
            "Min Rent",
            "Max Rent",
            "Treated Obs",
        ]
        summary.index = ["Never Treated", "Eventually Treated"]
<<<<<<< HEAD
=======

        logger.info("\n%s", summary.round(2))
>>>>>>> 1ebcfae (Added DIDDescriptiveAnalyzer and DIDTrendsVisualizer)

        return summary

    def _log_findings(
        self,
        df: pd.DataFrame,
        adoption_stats: dict[str, Any],
        pre_balance: pd.DataFrame,
        balance_test: dict[str, float],
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

                _ALPHA_005 = 0.05
                if balance_test["p_value"] < _ALPHA_005:
                    logger.warning(
                        "  Groups have statistically different pre-treatment rents (p < 0.05)"
                    )
                else:
                    logger.info(
                        "  No significant difference in pre-treatment rents (p >= 0.05)"
                    )
