"""Event Study Analysis for DiD.

This module estimates event study models to examine treatment effects
over time relative to the treatment date, providing a formal test of
parallel trends and showing how effects evolve.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from linearmodels import PanelOLS
from linearmodels.panel.results import PanelEffectsResults

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class EventStudyAnalyzer(Analyzer):
    """Estimate event study model for DiD analysis.

    This analyzer:
    1. Creates relative time dummies for periods around treatment
    2. Estimates TWFE model with these dummies (omitting k=-1 as reference)
    3. Extracts coefficients and confidence intervals
    4. Tests parallel trends using pre-treatment coefficients
    """

    def __init__(
        self,
        pre_periods: int = 12,
        post_periods: int = 36,
        reference_period: int = -1,
        output_path: str | None = None,
    ) -> None:
        """Initialize the event study analyzer.

        Args:
            pre_periods: Number of periods before treatment to include
            post_periods: Number of periods after treatment to include
            reference_period: Period to omit as reference (default: -1)
            output_path: Optional path to save results
        """
        super().__init__(
            "event_study_analysis",
            "Estimate event study model for dynamic treatment effects",
        )
        self.required_data = ["did_panel"]
        self.pre_periods = pre_periods
        self.post_periods = post_periods
        self.reference_period = reference_period
        self.output_path = output_path

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Estimate the event study model.

        Required context keys:
            - did_panel: DataFrame with DiD panel data including months_since_treatment

        Returns:
            Dictionary with:
            - event_study_results: Full PanelOLS results object
            - event_study_coefficients: DataFrame with coefficients and CIs
            - parallel_trends_test: Results of pre-trends test
        """
        did_panel = context["did_panel"].copy()

        logger.info("Estimating Event Study model...")
        logger.info(
            "  Event window: %d to +%d months", -self.pre_periods, self.post_periods
        )
        logger.info("  Reference period: k = %d", self.reference_period)

        # Step 1: Create relative time dummies
        panel, rel_time_cols = self._create_relative_time_dummies(did_panel)

        # Step 2: Estimate event study model
        results = self._estimate_event_study(panel, rel_time_cols)

        # Step 3: Extract coefficients
        coef_df = self._extract_coefficients(results, rel_time_cols)

        # Step 4: Test parallel trends
        parallel_trends_test = self._test_parallel_trends(results, coef_df)

        # Log results
        self._log_results(coef_df, parallel_trends_test)

        # Save results if output path specified
        if self.output_path:
            self._save_results(coef_df)

        return {
            "event_study_results": results,
            "event_study_coefficients": coef_df,
            "parallel_trends_test": parallel_trends_test,
        }

    def _create_relative_time_dummies(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[str]]:
        """Create dummy variables for each relative time period."""
        panel = df.copy()

        # Define event window
        event_window = range(-self.pre_periods, self.post_periods + 1)

        # Create dummies for each period (except reference)
        # Use 'm' prefix for negative (minus) and 'p' prefix for positive
        rel_time_cols = []
        for k in event_window:
            if k == self.reference_period:
                continue  # Skip reference period

            if k < 0:
                col_name = f"rel_time_m{abs(k)}"  # e.g., rel_time_m12 for -12
            else:
                col_name = f"rel_time_p{k}"  # e.g., rel_time_p0 for 0
            panel[col_name] = (panel["months_since_treatment"] == k).astype(float)
            rel_time_cols.append(col_name)

        # Set up panel index
        panel["treated"] = panel["treated"].astype(float)
        panel["rental_price"] = panel["rental_price"].astype(float)
        panel = panel.set_index(["tract_geoid", "month"])

        logger.info("  Created %d relative time dummies", len(rel_time_cols))

        return panel, rel_time_cols

    def _estimate_event_study(
        self, panel: pd.DataFrame, rel_time_cols: list[str]
    ) -> PanelEffectsResults:
        """Estimate the event study model."""
        logger.info("  Estimating model with entity and time fixed effects...")

        # Build formula with all relative time dummies
        formula = "rental_price ~ 1 + " + " + ".join(rel_time_cols)
        formula += " + EntityEffects + TimeEffects"

        model = PanelOLS.from_formula(formula, data=panel)
        results = model.fit(cov_type="clustered", cluster_entity=True)

        logger.info("  Model estimated successfully")

        return results

    def _extract_coefficients(
        self, results: PanelEffectsResults, rel_time_cols: list[str]
    ) -> pd.DataFrame:
        """Extract coefficients and confidence intervals."""

        # Parse relative time from column names
        # rel_time_m12 -> -12, rel_time_p0 -> 0, rel_time_p12 -> 12
        def parse_rel_time(col: str) -> int:
            if col.startswith("rel_time_m"):
                return -int(col.replace("rel_time_m", ""))
            elif col.startswith("rel_time_p"):
                return int(col.replace("rel_time_p", ""))
            else:
                raise ValueError(f"Unexpected column name format: {col}")

        coef_data = []
        for col in rel_time_cols:
            k = parse_rel_time(col)
            coef_data.append(
                {
                    "relative_time": k,
                    "coefficient": results.params[col],
                    "std_error": results.std_errors[col],
                    "t_stat": results.tstats[col],
                    "p_value": results.pvalues[col],
                }
            )

        coef_df = pd.DataFrame(coef_data)

        # Add reference period (coefficient = 0 by construction)
        ref_row = pd.DataFrame(
            {
                "relative_time": [self.reference_period],
                "coefficient": [0.0],
                "std_error": [0.0],
                "t_stat": [0.0],
                "p_value": [1.0],
            }
        )
        coef_df = pd.concat([coef_df, ref_row], ignore_index=True)

        # Sort by relative time
        coef_df = coef_df.sort_values("relative_time").reset_index(drop=True)

        # Calculate 95% CI
        coef_df["ci_lower"] = coef_df["coefficient"] - 1.96 * coef_df["std_error"]
        coef_df["ci_upper"] = coef_df["coefficient"] + 1.96 * coef_df["std_error"]

        return coef_df

    def _test_parallel_trends(
        self, results: PanelEffectsResults, coef_df: pd.DataFrame
    ) -> dict[str, Any]:
        """Test whether pre-treatment coefficients are jointly zero."""
        # Get pre-treatment coefficients (excluding reference period)
        pre_coefs = coef_df[
            (coef_df["relative_time"] < 0)
            & (coef_df["relative_time"] != self.reference_period)
        ].copy()

        if len(pre_coefs) == 0:
            return {
                "n_pre_periods": 0,
                "n_significant": 0,
                "conclusion": "No pre-periods",
            }

        # Count individually significant coefficients
        _ALPHA_005 = 0.05
        _PCT_SIGNIFICANT_THRESHOLD = 0.2
        _AVG_ABS_COEF_THRESHOLD_DOLLARS = 20.0
        n_significant = (pre_coefs["p_value"] < _ALPHA_005).sum()
        n_pre_periods = len(pre_coefs)

        # Average absolute pre-treatment coefficient
        avg_abs_coef = pre_coefs["coefficient"].abs().mean()

        # Simple heuristic: if more than 20% of pre-treatment coefficients
        # are significant, parallel trends may be violated
        if n_significant / n_pre_periods > _PCT_SIGNIFICANT_THRESHOLD:
            conclusion = (
                "Potential violation: multiple significant pre-treatment effects"
            )
        elif avg_abs_coef > _AVG_ABS_COEF_THRESHOLD_DOLLARS:
            conclusion = "Potential violation: large pre-treatment coefficients"
        else:
            conclusion = "Parallel trends plausible: pre-treatment effects near zero"

        return {
            "n_pre_periods": n_pre_periods,
            "n_significant": int(n_significant),
            "pct_significant": float(n_significant / n_pre_periods * 100),
            "avg_abs_pre_coef": float(avg_abs_coef),
            "conclusion": conclusion,
        }

    def _log_results(
        self, coef_df: pd.DataFrame, parallel_trends_test: dict[str, Any]
    ) -> None:
        """Log event study results."""
        logger.info("\n" + "=" * 60)
        logger.info("Event Study Results")
        logger.info("=" * 60)

        # Pre-treatment summary
        pre_coefs = coef_df[coef_df["relative_time"] < 0]
        post_coefs = coef_df[coef_df["relative_time"] >= 0]

        logger.info("\nPre-Treatment Coefficients (k < 0):")
        logger.info("  Mean: $%.2f", pre_coefs["coefficient"].mean())
        logger.info("  Std Dev: $%.2f", pre_coefs["coefficient"].std())
        logger.info(
            "  Range: [$%.2f, $%.2f]",
            pre_coefs["coefficient"].min(),
            pre_coefs["coefficient"].max(),
        )

        logger.info("\nPost-Treatment Coefficients (k >= 0):")
        logger.info("  Mean: $%.2f", post_coefs["coefficient"].mean())
        logger.info(
            "  Immediate effect (k=0): $%.2f",
            coef_df[coef_df["relative_time"] == 0]["coefficient"].to_numpy()[0],
        )

        # Parallel trends test
        logger.info("\nParallel Trends Test:")
        logger.info(
            "  Pre-treatment periods significant at 5%%: %d / %d (%.1f%%)",
            parallel_trends_test["n_significant"],
            parallel_trends_test["n_pre_periods"],
            parallel_trends_test["pct_significant"],
        )
        logger.info("  Conclusion: %s", parallel_trends_test["conclusion"])

    def _save_results(self, coef_df: pd.DataFrame) -> None:
        """Save coefficient results to CSV."""
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        coef_df.to_csv(output_path, index=False)
        logger.info("  Event study coefficients saved to: %s", output_path)
