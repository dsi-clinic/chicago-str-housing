"""Difference-in-Differences descriptive analyzer.

This module performs descriptive analysis for the Difference-in-Differences (DiD) analysis.
"""

import logging
from typing import Any

from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDDescriptiveAnalyzer(Analyzer):
    """Difference-in-Differences descriptive analyzer.

    This analyzer calculates descriptive statistics for the DiD analysis.
    """

    def __init__(self) -> None:
        """Initialize the Difference-in-Differences descriptive analyzer."""
        super().__init__(
            "did_descriptive_analysis",
            "Calculate descriptive statistics for the Difference-in-Differences analysis",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the Difference-in-Differences descriptive analyzer."""
        did_panel = context["did_panel"]
        # Count the unique treated tacts over time
        treated_by_month = (
            did_panel[did_panel["treated"] == 1]
            .groupby("month")["tract_geoid"]
            .nunique()
        )

        # Identify ever-treated vs never-treated tracts
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        did_panel["ever_treated"] = (
            did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        # Average rental price by ever_treated status and month
        avg_by_group = (
            did_panel.groupby(["month", "ever_treated"])["rental_price"]
            .mean()
            .unstack()
        )
        avg_by_group.columns = ["Never Treated", "Eventually Treated"]

        # Define pre-treatment period (before any tract is treated)
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
        pre_period = did_panel[did_panel["month"] < first_treatment]

        # Compare average pre-treatment rental prices
        pre_balance = pre_period.groupby("ever_treated")["rental_price"].agg(
            ["mean", "std", "count"]
        )
        pre_balance.index = ["Never Treated", "Eventually Treated"]

        never_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 0, "rental_price"
        ]
        eventually_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]

        t_stat, p_value = stats.ttest_ind(
            never_treated_prices, eventually_treated_prices
        )
        logger.info(f"t-statistics: {t_stat:.2f}, p-value: {p_value:.4f}")

        summary = did_panel.groupby("ever_treated").agg(
            {
                "tract_geoid": "nunique",
                "rental_price": ["mean", "std", "min", "max"],
                "treated": "sum",
            }
        )

        summary.columns = [
            "N Tracts",
            "Mean Rent",
            "Std Dev",
            "Min Rent",
            "Max Rent",
            "Treated Obs",
        ]
        summary.index = ["Never Treated", "Eventually Treated"]

        return {
            "treated_by_month": treated_by_month,
            "avg_by_group": avg_by_group,
            "pre_balance": pre_balance,
            "t_stat": t_stat,
            "p_value": p_value,
            "summary": summary,
        }
