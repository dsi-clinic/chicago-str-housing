"""Event study analyzer."""

import logging
from typing import Any

import pandas as pd
from linearmodels import PanelOLS
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

class EventStudyAnalyzer(Analyzer):
    """Event study analyzer."""

    def __init__(self) -> None:
        """Initialize the event study analyzer."""
        super().__init__("event_study_analyzer", "Event study analyzer")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the event study analyzer."""
        logger.info("Executing event study analyzer")
        did_panel = context["did_panel"]
        # Define the event window (e.g., 12 months before/after)
        event_window = range(-12, 13)  # -12 to +12

        # Create dummies for each relative time period
        # Use naming convention that avoids negative signs in column names
        # (formula parser interprets '-' as subtraction)
        rel_time_col_map = {}  # Maps relative time k to column name
        for k in event_window:
            if k == -1:  # Skip reference period
                continue
            # Use 'm' prefix for negative numbers to avoid '-' in column names
            col_name = f"rel_time_m{abs(k)}" if k < 0 else f"rel_time_{k}"
            rel_time_col_map[k] = col_name
            did_panel[col_name] = (
                did_panel["months_since_treatment"] == k
            ).astype(int)

        # Get list of dummy column names
        rel_time_cols = list(rel_time_col_map.values())

        panel = did_panel.set_index(["tract_geoid", "month"])

        # Build formula with all relative time dummies
        formula = "rental_price ~ 1 + " + " + ".join(rel_time_cols) + " + EntityEffects + TimeEffects"

        logger.info("Formula: %s", formula)
        model = PanelOLS.from_formula(
            formula,
            data=panel
        )

        results = model.fit(cov_type="clustered", cluster_entity=True)
        logger.info("Event study results: %s", results.summary)

        # Extract coefficients and confidence intervals
        # Map column names back to relative time values
        relative_times = []
        coefficients = []
        std_errors = []
        for k, col_name in rel_time_col_map.items():
            relative_times.append(k)
            coefficients.append(results.params[col_name])
            std_errors.append(results.std_errors[col_name])
        
        coef_df = pd.DataFrame({
            "relative_time": relative_times,
            "coefficient": coefficients,
            "std_error": std_errors,
        })

        # Add reference period (coefficient = 0 by construction)
        ref_row = pd.DataFrame({"relative_time": [-1], "coefficient": [0], "std_error": [0]})
        coef_df = pd.concat([coef_df, ref_row]).sort_values("relative_time")

        # Calculate 95% CI
        coef_df["ci_lower"] = coef_df["coefficient"] - 1.96 * coef_df["std_error"]
        coef_df["ci_upper"] = coef_df["coefficient"] + 1.96 * coef_df["std_error"]
        logger.info("Coefficient dataframe: %s", coef_df)

        # Get pre-treatment coefficients
        pre_coefs = [results.params[rel_time_col_map[k]] for k in range(-12, -1)]
        pre_ses = [results.std_errors[rel_time_col_map[k]] for k in range(-12, -1)]

        # Simple check: How many are individually significant?
        SIGNIFICANCE_LEVEL = 0.05
        pre_pvals = [2 * (1 - stats.norm.cdf(abs(c/s))) for c, s in zip(pre_coefs, pre_ses)]
        n_significant = sum(p < SIGNIFICANCE_LEVEL for p in pre_pvals)
        print(f"Pre-treatment coefficients significant at 5%: {n_significant} / {len(pre_coefs)}")

        return {"event_study_results": results, "event_study_model": model, "event_study_coef_df": coef_df}