"""Event study analyzer for dynamic DiD effects.

This module estimates separate effects for each period relative to treatment.
"""

import logging
from typing import Any

import pandas as pd
from linearmodels.panel import PanelOLS
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class EventStudyAnalyzer(Analyzer):
    """Estimate separate effects for each period relative to treatment."""

    def __init__(self, event_window: int = 12) -> None:
        """Initialize the event-study analyzer.

        Args:
            event_window: Number of months before/after treatment to include
                in the relative-time window (e.g., 12 → -12..+12).
        """
        super().__init__(
            "event_study_analyzer",
            "Estimate dynamic DiD effects using an event-study TWFE model",
        )
        self.event_window = int(event_window)
        self.required_data = ["did_panel"]
        self.output_data = ["event_study_results", "event_study_coef_df"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the event-study model and return coefficients and tests."""
        did_panel = context["did_panel"].copy()
        panel = did_panel.set_index(["tract_geoid", "month"])

        # Define event window, e.g. -12..+12
        event_window = range(-self.event_window, self.event_window + 1)

        # Create relative-time dummies, skipping -1 as reference period
        rel_time_cols: list[str] = []
        for k in event_window:
            if k == -1:
                continue  # reference period
            col = f"rel_time_{k}"
            panel[col] = (panel["months_since_treatment"] == k).astype(float)
            rel_time_cols.append(col)

        # Outcome and regressors
        y = panel["rental_price"].astype(float)
        X = panel[rel_time_cols]

        logger.info(
            "Fitting event-study TWFE model with PanelOLS over window %d..%d",
            event_window.start,
            event_window.stop - 1,
        )

        # Model estimation
        model = PanelOLS(y, X, entity_effects=True, time_effects=True)
        results = model.fit(cov_type="clustered", cluster_entity=True)

        # Build coefficient DataFrame
        rel_times: list[int] = []
        coefs: list[float] = []
        ses: list[float] = []
        pvals: list[float] = []

        for col in rel_time_cols:
            k = int(col.split("_")[-1])
            if col not in results.params.index:
                # If col was dropped (e.g., collinearity), mark as NaN
                rel_times.append(k)
                coefs.append(float("nan"))
                ses.append(float("nan"))
                pvals.append(float("nan"))
                continue
            rel_times.append(k)
            coef_k = float(results.params[col])
            se_k = float(results.std_errors[col])
            coefs.append(coef_k)
            ses.append(se_k)
            if se_k == 0 or pd.isna(coef_k) or pd.isna(se_k):
                pvals.append(float("nan"))
            else:
                z_k = abs(coef_k / se_k)
                pvals.append(float(2 * (1 - stats.norm.cdf(z_k))))

        coef_df = pd.DataFrame(
            {
                "relative_time": rel_times,
                "coefficient": coefs,
                "std_error": ses,
                "p_value": pvals,
            }
        )

        # Add reference period (-1) with coefficient 0 by construction
        ref_row = pd.DataFrame(
            {
                "relative_time": [-1],
                "coefficient": [0.0],
                "std_error": [0.0],
                "p_value": [1.0],
            }
        )
        coef_df = pd.concat([coef_df, ref_row], ignore_index=True).sort_values(
            "relative_time"
        )

        # 95% confidence intervals
        coef_df["ci_lower"] = coef_df["coefficient"] - 1.96 * coef_df["std_error"]
        coef_df["ci_upper"] = coef_df["coefficient"] + 1.96 * coef_df["std_error"]

        # Parallel trends check
        pre_ks = list(range(-self.event_window, -1))
        pre_coefs = []
        pre_ses = []
        for k in pre_ks:
            col = f"rel_time_{k}"
            if col in results.params.index:
                pre_coefs.append(float(results.params[col]))
                pre_ses.append(float(results.std_errors[col]))

        pre_pvals: list[float] = []
        if pre_coefs and pre_ses:
            for c, s in zip(pre_coefs, pre_ses, strict=False):
                if s == 0 or pd.isna(c) or pd.isna(s):
                    pre_pvals.append(float("nan"))
                    continue
                z = abs(c / s)
                pre_pvals.append(float(2 * (1 - stats.norm.cdf(z))))

        n_significant = sum(
            1 for p in pre_pvals if p is not None and not pd.isna(p) and p < 0.05
        )
        n_tests = len([p for p in pre_pvals if p is not None and not pd.isna(p)])

        logger.info(
            "Pre-treatment coefficients significant at 5%%: %d / %d",
            n_significant,
            n_tests,
        )

        pre_trends_summary = {
            "pre_ks": pre_ks,
            "pre_coefs": pre_coefs,
            "pre_ses": pre_ses,
            "pre_pvals": pre_pvals,
            "n_significant_5pct": n_significant,
            "n_tests": n_tests,
        }

        return {
            "event_study_results": {
                "model_results": results,
                "pre_trends": pre_trends_summary,
            },
            "event_study_coef_df": coef_df,
        }
