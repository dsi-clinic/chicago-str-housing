"""Difference-in-Differences descriptive analyzer.

This module returbns count of treated vs. never treated tracts, average rental prices by group and month, pre-treatment balance statistics, and summary statistics for the DID panel data.
"""

import logging
from pathlib import Path
from typing import Any

from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDDescriptiveAnalyzer(Analyzer):
    """Analyze difference-in-differences descriptive analysis.

    This demonstrates analysis of the DID panel data.
    It returns count of treated vs. never treated tracts, average rental prices by group and month, pre-treatment balance statistics, and summary statistics for the DID panel data.
    """

    def __init__(self) -> None:
        """Initialize the DID descriptive analyzer."""
        super().__init__(
            "did_descriptive_analysis",
            "Analyze correlations in census tract rental data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform DID descriptive analysis."""
        logger.info("Performing statistical analysis on DID panel data...")

        did_panel = context["did_panel_data"]

        # Count of treated vs. never-treated tracts
        adoption = (
            did_panel.groupby("month")["treated"].sum()  # Count of treated tract-months
        )

        # Unique treated tracts over time
        treated_by_month = (
            did_panel[did_panel["treated"] == 1]
            .groupby("month")["tract_geoid"]
            .nunique()
        )

        # Average rental prices by group and month
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        did_panel["ever_treated"] = did_panel["tract_geoid"].isin(ever_treated_tracts)

        # Count of tract-months: treated vs control per month
        treatment_count = did_panel.pivot_table(
            index="month",
            columns="treated",
            values="tract_geoid",
            aggfunc="count",
            fill_value=0,
        )
        treatment_count.columns = ["Not Treated", "Treated This Month"]

        did_panel["ever_treated"] = did_panel["tract_geoid"].isin(ever_treated_tracts)

        avg_by_group = did_panel.pivot_table(
            index="month",
            columns="ever_treated",
            values="rental_price",
            aggfunc="mean",
        )
        avg_by_group.columns = ["Never Treated", "Eventually Treated"]

        # Pre-treatment balance statistics
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
        pre_period = did_panel[did_panel["month"] < first_treatment]

        pre_balance = pre_period.groupby("ever_treated")["rental_price"].agg(
            ["mean", "std", "count"]
        )
        pre_balance.index = ["Never Treated", "Eventually Treated"]
        logger.info("Calculated pre-treatment balance statistics:")

        # Statistical test, t-test
        never_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 0, "rental_price"
        ]
        eventually_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]

        t_stat, p_value = stats.ttest_ind(
            never_treated_prices, eventually_treated_prices
        )
        pre_balance_stats = {"t_stat": float(t_stat), "p_value": float(p_value)}
        logger.info("Calculated pre-treatment balance statistics")

        # Summary statistics table
        summary = did_panel.groupby("ever_treated").agg(
            {
                "tract_geoid": "nunique",
                "rental_price": ["mean", "std", "min", "max"],
                "treated": "sum",  # Total treated tract-months
            }
        )

        summary.columns = [
            "N Tracts",
            "Mean Price",
            "Std Dev",
            "Min Rent",
            "Max Price",
            "Treated Obs",
        ]
        summary.index = ["Never Treated", "Eventually Treated"]
        logger.info("Calculated summary statistics")

        output_dir = Path("/project/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "did_descriptive_analysis.txt"

        with Path(report_path).open("w") as f:
            f.write("DID Descriptive Analysis\n")
            f.write("=" * 50 + "\n\n")
            f.write("Count of treated vs. never-treated tracts\n")
            f.write(treatment_count.to_string() + "\n\n")
            f.write("Average rental prices by group and month\n")
            f.write(avg_by_group.to_string() + "\n\n")
            f.write("Pre-treatment balance (rental price)\n")
            f.write(pre_balance.to_string() + "\n\n")
            f.write("Pre-treatment t-test\n")
            f.write(f"  t-statistic: {pre_balance_stats['t_stat']:.4f}\n")
            f.write(f"  p-value:     {pre_balance_stats['p_value']:.4f}\n\n")
            f.write("Summary statistics by group\n")
            f.write(summary.round(2).to_string() + "\n\n")

        logger.info("Wrote analysis report to: %s", report_path)

        return {
            "adoption_data": adoption,
            "treated_by_month": treated_by_month,
            "avg_by_group": avg_by_group,
            "pre_period": pre_period,
            "pre_balance": pre_balance,
            "pre_balance_stats": pre_balance_stats,
            "first_treatment": first_treatment,
        }
