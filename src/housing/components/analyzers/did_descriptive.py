"""Module for descriptive analysis of DiD panel dataset:

1. Split data between eventually-treated and never treated-tracts for analysis
2. Conduct t-test on pre-treatment balance
3. Prepare per-group averaged data for visualizing parallel trends check.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDDescriptiveAnalyzer(Analyzer):
    """Analyze DiD data prior to conducting experiment and check for the parallel trends assumption."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the DiD descriptive analyzer."""
        super().__init__(
            "did_descriptive_analyzer",
            "Analyze DiD dataset before experiment",
        )
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze DiD Descriptive Trends Before Conducting Experiment."""
        did_panel = context["did_panel"]

        # Identify ever-treated vs never-treated tracts
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        did_panel["ever_treated"] = (
            did_panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        n_treated = int(ever_treated.sum())

        logger.info(
            "Number of tracts: %d eventually-treated and %d never-treated",
            n_treated,
            len(ever_treated) - n_treated,
        )

        # Average rental price by ever_treated status and month
        avg_by_group = did_panel.pivot_table(
            values="rental_price", index="month", columns="ever_treated", aggfunc="mean"
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

        # Conduct t-test on pre-treatment trends

        never_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 0, "rental_price"
        ]
        eventually_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]

        t_stat, p_value = stats.ttest_ind(
            never_treated_prices, eventually_treated_prices
        )

        ALPHA = 0.05

        t_test_results_df = pd.DataFrame(
            {
                "t_stat": [t_stat],
                "p_value": [p_value],
                "significant_5pct": [p_value < ALPHA],
            }
        )

        if p_value < ALPHA:
            logger.info(
                "Significant difference in pre-treatment balance -- t-statistic: %.2f, p-value: %.4f",
                t_stat,
                p_value,
            )
        else:
            logger.info(
                "t-statistic: %.2f, p-value: %.4f (Not significant)", t_stat, p_value
            )

        summary = did_panel.groupby("ever_treated").agg(
            {
                "tract_geoid": "nunique",
                "rental_price": ["mean", "std", "min", "max"],
                "treated": "sum",  # Total treated tract-months
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

        t_test_output_path = Path(self.output_dir) / "pre_treatment_balance_test.csv"
        t_test_results_df.to_csv(t_test_output_path, index=False)

        summary_output_path = (
            Path(self.output_dir) / "did_descriptive_summary_stats.csv"
        )
        summary.to_csv(summary_output_path)

        return {
            "average_rent_by_treatment_group": avg_by_group,
            "did_summary_statistics": str(summary_output_path),  # path to csv output
            "pre_treatment_balance_test_result": str(
                t_test_output_path
            ),  # path to csv output
        }
