"""Implements an event-study (dynamic DiD) estimator using two-way fixed effects.

Checks for parallel trends assumption
"""

import logging
from typing import Any

import pandas as pd
from linearmodels.panel import PanelOLS
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class EventStudyAnalyzer(Analyzer):
    """Run a two-way fixed-effects event study around treatment timing."""

    def __init__(self, panel: str | None = None) -> None:
        """Initialize the analyzer with the panel key.

        Args:
            panel: Context key containing the panel DataFrame (default: "did_panel").
        """
        super().__init__(
            "event_study_analyzer",
            "Estimate dynamic treatment effects via event-study specification.",
        )
        self.panel = panel or "did_panel"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the event-study regression on the provided panel data."""
        did_panel = context[self.panel].copy()

        # Define the event window (e.g., 12 months before/after)
        event_window = range(-12, 13)  # -12 to +12

        # Create dummies for each relative time period
        rel_time_cols = []

        for k in event_window:
            if k == -1:  # Skip reference period
                continue
            if k < 0:
                column_name = f"rel_time_negative_{abs(k)}"
            else:
                column_name = f"rel_time_{k}"

            did_panel[column_name] = (did_panel["months_since_treatment"] == k).astype(
                int
            )

            rel_time_cols.append(column_name)

        # Set up panel
        panel = did_panel.set_index(["tract_geoid", "month"])

        # Build formula with all relative time dummies
        formula = "rental_price ~ 1 + " + " + ".join(rel_time_cols)
        formula += " + EntityEffects + TimeEffects"

        model = PanelOLS.from_formula(formula, data=panel)

        results = model.fit(cov_type="clustered", cluster_entity=True)

        # Extract coefficients and confidence intervals
        coef_df = pd.DataFrame(
            {
                "relative_time": [r for r in event_window if r != -1],
                "coefficient": [results.params[col] for col in rel_time_cols],
                "std_error": [results.std_errors[col] for col in rel_time_cols],
            }
        )

        # Add reference period (coefficient = 0 by construction)
        ref_row = pd.DataFrame(
            {"relative_time": [-1], "coefficient": [0], "std_error": [0]}
        )
        coef_df = pd.concat([coef_df, ref_row]).sort_values("relative_time")

        # Calculate 95% CI
        coef_df["ci_lower"] = coef_df["coefficient"] - 1.96 * coef_df["std_error"]
        coef_df["ci_upper"] = coef_df["coefficient"] + 1.96 * coef_df["std_error"]

        # Get pre-treatment coefficients
        pre_coefs = [
            results.params[f"rel_time_negative_{abs(k)}"] for k in range(-12, -1)
        ]
        pre_ses = [
            results.std_errors[f"rel_time_negative_{abs(k)}"] for k in range(-12, -1)
        ]

        # Simple check: How many are individually significant?
        significance_level = 0.05
        pre_pvals = [
            2 * (1 - stats.norm.cdf(abs(c / s))) for c, s in zip(pre_coefs, pre_ses)
        ]
        n_significant = sum(p < significance_level for p in pre_pvals)

        logger.info(
            "Pre-treatment coefficients significant at 5%% : %d / %d",
            n_significant,
            len(pre_coefs),
        )

        return {"event_study_coefficients": coef_df}
