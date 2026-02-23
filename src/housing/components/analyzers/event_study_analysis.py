"""Event study analyzer.

This module:
- estimates the event study model
- tests for parallel trends
- returns the event study results
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from linearmodels import PanelOLS
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class EventStudyAnalyzer(Analyzer):
    """Estimate the event study model and test for parallel trends.

    This module:
    - estimates the event study model
    - tests for parallel trends
    - returns the event study results
    """

    def __init__(self, output_dir: str | None = None, filename_suffix: str | None = None) -> None:
        """Initialize the event study analyzer."""
        self.output_dir = output_dir or "/project/output"
        self.filename_suffix = filename_suffix or ""
        super().__init__(
            "event_study_analysis",
            "Estimate the event study model",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Estimate the event study model."""
        logger.info("Estimating the event study model")

        did_panel = context["did_panel_data"].copy()

        def rel_time_col(k: int) -> str:
            """Helper function to create relative time column names"""
            return f"rel_time_neg{-k}" if k < 0 else f"rel_time_{k}"

        def parse_rel_time(col: str) -> int:
            """Helper function to convert relative time column names back to relative time"""
            if col.startswith("rel_time_neg"):
                return -int(col.replace("rel_time_neg", ""))
            return int(col.replace("rel_time_", ""))

        # create relative time dummies
        event_window = range(-12, 13)
        for k in event_window:
            if k == -1:  # skip reference period
                continue
            did_panel[rel_time_col(k)] = (
                did_panel["months_since_treatment"] == k
            ).astype(int)

        rel_time_cols = [rel_time_col(k) for k in event_window if k != -1]

        # set panel index and build formula
        panel = did_panel.set_index(["tract_geoid", "month"])
        formula = "rental_price ~ 1 + " + " + ".join(rel_time_cols)

        # estimate the model
        model = PanelOLS.from_formula(
            formula + " + EntityEffects + TimeEffects",
            data=panel,
        )
        results = model.fit(cov_type="clustered", cluster_entity=True)

        # extract coefficients and confidence intervals
        coef_df = pd.DataFrame(
            {
                "relative_time": [parse_rel_time(col) for col in rel_time_cols],
                "coefficient": [results.params[col] for col in rel_time_cols],
                "std_error": [results.std_errors[col] for col in rel_time_cols],
            }
        )

        # add reference period (coefficient = 0 by construction)
        ref_row = pd.DataFrame(
            {"relative_time": [-1], "coefficient": [0], "std_error": [0]}
        )
        coef_df = pd.concat([coef_df, ref_row]).sort_values("relative_time")

        # 95% confidence interval
        coef_df["ci_lower"] = coef_df["coefficient"] - 1.96 * coef_df["std_error"]
        coef_df["ci_upper"] = coef_df["coefficient"] + 1.96 * coef_df["std_error"]

        # Get pre-treatment coefficients
        pre_coefs = [results.params[rel_time_col(k)] for k in range(-12, -1)]
        pre_ses = [results.std_errors[rel_time_col(k)] for k in range(-12, -1)]

        # Simple check: How many are individually significant?
        alpha = 0.05
        pre_pvals = [
            2 * (1 - stats.norm.cdf(abs(c / s))) for c, s in zip(pre_coefs, pre_ses)
        ]
        n_significant = sum(p < alpha for p in pre_pvals)

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base = "event_study_analysis"
        name = f"{base}{self.filename_suffix}.txt" if self.filename_suffix else f"{base}.txt"
        report_path = output_dir / name

        with Path(report_path).open("w") as f:
            f.write("Event Study Analysis\n")
            f.write("=" * 50 + "\n\n")
            f.write("Results\n")
            f.write(coef_df.to_string() + "\n\n")
            f.write("95% Confidence Interval\n")
            f.write(coef_df[["ci_lower", "ci_upper"]].to_string() + "\n\n")
            f.write(
                f"Pre-treatment coefficients significant at 5%: {n_significant} / {len(pre_coefs)}\n\n"
            )
            f.write(results.summary.as_text() + "\n\n")

        logger.info("Wrote event studyanalysis report to: %s", report_path)

        return {
            "coef_df": coef_df,
        }
