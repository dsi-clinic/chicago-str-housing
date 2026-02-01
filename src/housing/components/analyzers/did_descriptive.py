"""Difference-in-differences descriptive analyzer.

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
    """Perform descriptive analysis for difference-in-differences.

    This analyzer:
    1. Counts treated vs. never-treated tracts
    2. Computes average rental prices by group and month
    3. Analyzes pre-treatment balance (comparing treated vs control before treatment)
    4. Creates summary statistics table
    """

    def __init__(self) -> None:
        """Initialize the DiD descriptive analyzer."""
        super().__init__(
            "did_descriptive_analysis",
            "Perform descriptive analysis for difference-in-differences",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform descriptive analysis on DiD panel data.

        Args:
            context: Pipeline context containing:
                - did_panel: DataFrame with tract_geoid, month, rental_price,
                            first_prohibition_date, treated, months_since_treatment

        Returns:
            Dictionary with analysis results including:
                - tract_counts: Count of treated vs never-treated tracts
                - avg_rent_by_group_month: DataFrame with month as index and columns
                  "Never Treated" and "Eventually Treated" showing average rental prices
                - pre_treatment_balance: DataFrame with pre-treatment balance statistics
                  by group (Never Treated, Eventually Treated) with columns: mean, std, count
                - summary_stats: Summary statistics table
        """
        did_panel = context["did_panel"]

        # Identify ever-treated vs never-treated tracts
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        did_panel["ever_treated"] = (
            did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        # Step 1: Count treated vs. never-treated tracts
        tract_counts = self._count_tracts(did_panel)
        logger.info("  Treated tracts: %d", tract_counts["treated_tracts"])
        logger.info("  Never-treated tracts: %d", tract_counts["never_treated_tracts"])
        logger.info("  Total tracts: %d", tract_counts["total_tracts"])

        # Step 2: Average rental prices by group and month
        avg_rent_by_group_month = self._compute_avg_rent_by_group_month(did_panel)
        logger.info("  Computed averages for %d months", len(avg_rent_by_group_month))

        # Step 3: Pre-treatment balance statistics
        pre_treatment_balance = self._compute_pre_treatment_balance(did_panel)
        logger.info("  Pre-treatment balance statistics:")
        logger.info("\n%s", pre_treatment_balance)

        # Step 4: Summary statistics table
        summary_stats = self._create_summary_stats_table(did_panel)
        logger.info("  Summary statistics computed")

        return {
            "tract_counts": tract_counts,
            "avg_rent_by_group_month": avg_rent_by_group_month,
            "pre_treatment_balance": pre_treatment_balance,
            "summary_stats": summary_stats,
        }

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
        )
        avg_by_group.columns = ["Never Treated", "Eventually Treated"]

        return avg_by_group

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

        # Compare average pre-treatment rental prices
        pre_balance = pre_period.groupby("ever_treated")["rental_price"].agg(
            ["mean", "std", "count"]
        )
        pre_balance.index = ["Never Treated", "Eventually Treated"]

        # Perform t-test to compare groups
        never_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 0, "rental_price"
        ]
        eventually_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]

        t_stat, p_value = stats.ttest_ind(
            never_treated_prices, eventually_treated_prices
        )
        logger.info("  t-statistic: %.2f, p-value: %.4f", t_stat, p_value)

        return pre_balance

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
        summary.columns = [
            "N Tracts",
            "Mean Rent",
            "Std Dev",
            "Min Rent",
            "Max Rent",
            "Treated Obs",
        ]
        summary.index = ["Never Treated", "Eventually Treated"]

        logger.info("\n%s", summary.round(2))

        return summary
