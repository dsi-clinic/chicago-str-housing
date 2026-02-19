
import logging
from typing import Any

import pandas as pd
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class DIDDescriptiveAnalyzer(Analyzer):
    """Analyze DiD panel data for descriptive statistics and pre-treatment checks."""

    def __init__(self) -> None:
        """Initialize the DiD descriptive analyzer."""
        super().__init__(
            "did_descriptive_analysis",
            "Descriptive analysis for Diff-in-Diff estimation",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform DiD descriptive analysis."""
        logger.info("Starting DiD descriptive analysis...")

        did_panel = context.get("did_panel")
        if did_panel is None:
            logger.error("did_panel not found in context")
            raise ValueError("did_panel not found in context")

        # Create a copy to avoid modifying the original dataframe in context
        # unless intended
        analysis_df = did_panel.copy()

        # 1. Adoption over time
        # Count treated tracts by month
        adoption = analysis_df.groupby("month")["treated"].sum()

        # Unique treated tracts over time
        treated_by_month = (
            analysis_df[analysis_df["treated"] == 1]
            .groupby("month")["tract_geoid"]
            .nunique()
        )

        # 2. Identify ever-treated vs never-treated
        ever_treated = analysis_df.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        analysis_df["ever_treated"] = (
            analysis_df["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        # 3. Average outcomes by group
        avg_by_group = (
            analysis_df.groupby(["month", "ever_treated"])["rental_price"]
            .mean()
            .unstack()
        )
        avg_by_group.columns = ["Never Treated", "Eventually Treated"]

        # 4. Pre-treatment balance
        # Find first treatment date
        # Assuming treated == 1 indicates the post-treatment period for that unit
        # However, staggered adoption means "first treatment" effectively splits pre/post for the whole cohort if we define it that way
        # For the lesson purpose, it looks like there's a global "first treatment" date or we define pre-period
        # as before ANY tract is treated.
        
        # Determine the earliest date any tract was treated
        treated_rows = analysis_df[analysis_df["treated"] == 1]
        if not treated_rows.empty:
            first_treatment = treated_rows["month"].min()
        else:
            logger.warning("No treated units found. Cannot determine first treatment date.")
            first_treatment = analysis_df["month"].min() # Fallback

        pre_period = analysis_df[analysis_df["month"] < first_treatment]

        pre_balance = (
            pre_period.groupby("ever_treated")["rental_price"]
            .agg(["mean", "std", "count"])
        )
        pre_balance.index = ["Never Treated", "Eventually Treated"]

        # T-test
        never_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 0, "rental_price"
        ]
        eventually_treated_prices = pre_period.loc[
            pre_period["ever_treated"] == 1, "rental_price"
        ]

        # Use nan_policy='omit' to handle missing values if any
        t_stat, p_value = stats.ttest_ind(
            never_treated_prices, eventually_treated_prices, nan_policy="omit"
        )

        # 5. Summary statistics table
        summary = analysis_df.groupby("ever_treated").agg(
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

        logger.info(f"DiD Analysis Complete. First treatment observed: {first_treatment}")
        logger.info(
            f"Pre-treatment balance t-stat: {t_stat:.2f}, p-value: {p_value:.4f}"
        )

        return {
            "did_adoption_curve": treated_by_month,
            "did_avg_by_group": avg_by_group,
            "did_pre_balance": pre_balance,
            "did_balance_t_test": {"t_stat": t_stat, "p_value": p_value},
            "did_summary_table": summary,
            "did_first_treatment_date": first_treatment,
            # Pass the enhanced dataframe if needed, or reliance on input
            "did_analysis_df": analysis_df, 
        }
