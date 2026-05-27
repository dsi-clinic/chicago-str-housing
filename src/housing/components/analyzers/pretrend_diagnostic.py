"""Pre-trend diagnostic analysis for Difference-in-Differences.

Investigates why pre-treatment trends diverge between treated and control groups
by analyzing observable tract characteristics and testing parallel trends formally.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

SIGNIFICANCE_LEVEL = 0.05
BALANCE_THRESHOLD = 0.1  # |Cohen's d| threshold for imbalance


class PretrendDiagnosticAnalyzer(Analyzer):
    """Diagnose pre-treatment trend divergence and test parallel trends assumption."""

    def __init__(self, output_dir: str | Path | None = None) -> None:
        """Initialize the diagnostic analyzer.

        Args:
            output_dir: If set, write CSV summaries for reproducible slide/brief references.
        """
        super().__init__(
            "pretrend_diagnostic",
            "Analyze pre-treatment trends and test parallel trends assumption",
        )
        self.output_dir = Path(output_dir) if output_dir else None

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run pre-trend diagnostic analysis."""
        logger.info("Starting pre-trend diagnostic analysis...")

        # Get panel with covariates
        did_panel = context.get("did_panel_with_covariates")
        if did_panel is None:
            did_panel = context.get("did_panel")
        if did_panel is None:
            raise ValueError("No DID panel found in context")

        panel = did_panel.copy()

        # 1. Compare tract characteristics by treatment status
        tract_comparison = self._compare_tract_characteristics(panel)

        # 2. Test for differential pre-trends
        pretrend_test = self._test_pretrends(panel)

        # 3. Analyze pre-treatment rental price divergence
        rent_divergence = self._analyze_rent_divergence(panel)

        # 4. Check balance on covariates
        balance_check = self._check_covariate_balance(panel)

        # Log key findings
        self._log_diagnostic_summary(tract_comparison, pretrend_test, rent_divergence)

        if self.output_dir is not None:
            self._export_csv_tables(
                tract_comparison,
                pretrend_test,
                rent_divergence,
                balance_check,
                self.output_dir,
            )

        return {
            "pretrend_tract_comparison": tract_comparison,
            "pretrend_test_results": pretrend_test,
            "pretrend_rent_divergence": rent_divergence,
            "pretrend_balance_check": balance_check,
        }

    def _export_csv_tables(
        self,
        tract_comparison: pd.DataFrame,
        pretrend_test: dict[str, Any],
        rent_divergence: pd.DataFrame,
        balance_check: dict[str, Any],
        output_dir: Path,
    ) -> None:
        """Write diagnostic tables alongside other DiD CSV outputs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        if not tract_comparison.empty:
            tract_comparison.to_csv(
                output_dir / "pretrend_tract_comparison.csv", index=False
            )
        if not rent_divergence.empty:
            rent_divergence.to_csv(output_dir / "pretrend_rent_gap_by_month.csv")
        pt_row = dict(pretrend_test)
        pd.DataFrame([pt_row]).to_csv(
            output_dir / "pretrend_parallel_trends_regression_summary.csv",
            index=False,
        )
        bc = balance_check.copy()
        if isinstance(bc.get("imbalanced_covariates"), list):
            bc["imbalanced_covariates"] = "; ".join(bc["imbalanced_covariates"])
        pd.DataFrame([bc]).to_csv(
            output_dir / "pretrend_balance_summary.csv",
            index=False,
        )

    def _compare_tract_characteristics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compare observable characteristics between treated and control tracts."""
        # Get one observation per tract
        tract_data = df.drop_duplicates(subset="tract_geoid").copy()

        # Define treatment groups
        if "ever_treated" not in tract_data.columns:
            tract_data["ever_treated"] = tract_data.groupby("tract_geoid")[
                "treated"
            ].transform("max")

        # Covariates to compare
        covariates = [
            "median_income",
            "median_house_value",
            "baseline_rent",
            "pct_bachelor",
            "pct_rented",
            "median_age",
            "total_population",
        ]

        # Keep only available covariates
        available_covariates = [c for c in covariates if c in tract_data.columns]

        if not available_covariates:
            logger.warning("No covariates available for comparison")
            return pd.DataFrame()

        results = []

        for cov in available_covariates:
            treated_vals = tract_data.loc[tract_data["ever_treated"] == 1, cov].dropna()
            control_vals = tract_data.loc[tract_data["ever_treated"] == 0, cov].dropna()

            if len(treated_vals) == 0 or len(control_vals) == 0:
                continue

            # Calculate summary statistics
            treated_mean = treated_vals.mean()
            control_mean = control_vals.mean()
            diff = treated_mean - control_mean
            pct_diff = (diff / control_mean * 100) if control_mean != 0 else np.nan

            # T-test for difference in means
            t_stat, p_value = stats.ttest_ind(
                treated_vals, control_vals, equal_var=False
            )

            # Standardized mean difference (Cohen's d)
            pooled_std = np.sqrt((treated_vals.var() + control_vals.var()) / 2)
            cohens_d = diff / pooled_std if pooled_std > 0 else np.nan

            results.append(
                {
                    "covariate": cov,
                    "treated_mean": treated_mean,
                    "control_mean": control_mean,
                    "difference": diff,
                    "pct_difference": pct_diff,
                    "t_statistic": t_stat,
                    "p_value": p_value,
                    "cohens_d": cohens_d,
                    "significant": p_value < SIGNIFICANCE_LEVEL,
                    "n_treated": len(treated_vals),
                    "n_control": len(control_vals),
                }
            )

        comparison_df = pd.DataFrame(results)

        return comparison_df

    def _test_pretrends(self, df: pd.DataFrame) -> dict[str, Any]:
        """Test for differential pre-treatment trends (parallel trends test)."""
        # Define pre-treatment period
        first_treatment = df.loc[df["treated"] == 1, "month"].min()

        if pd.isna(first_treatment):
            logger.warning("No treated observations found")
            return {"error": "No treated observations"}

        pre_period = df[df["month"] < first_treatment].copy()

        if len(pre_period) == 0:
            logger.warning("No pre-treatment observations")
            return {"error": "No pre-treatment observations"}

        # Define ever_treated
        if "ever_treated" not in pre_period.columns:
            pre_period["ever_treated"] = pre_period["tract_geoid"].map(
                df.groupby("tract_geoid")["treated"].max()
            )

        # Create time trend (months since first observation)
        pre_period["time_trend"] = (
            (pre_period["month"] - pre_period["month"].min()).dt.days / 30.44
        ).astype(int)

        # Regression: rent ~ ever_treated + time_trend + ever_treated × time_trend + tract_FE
        # The interaction coefficient tests for differential trends

        try:
            import statsmodels.formula.api as smf

            # Create interaction term
            pre_period["treated_x_time"] = (
                pre_period["ever_treated"] * pre_period["time_trend"]
            )

            # Simple model without fixed effects for illustration
            model = smf.ols(
                "rental_price ~ ever_treated + time_trend + treated_x_time",
                data=pre_period,
            ).fit()

            interaction_coef = model.params.get("treated_x_time", np.nan)
            interaction_se = model.bse.get("treated_x_time", np.nan)
            interaction_pval = model.pvalues.get("treated_x_time", np.nan)

            result = {
                "interaction_coef": interaction_coef,
                "interaction_se": interaction_se,
                "p_value": interaction_pval,
                "significant": interaction_pval < SIGNIFICANCE_LEVEL
                if not pd.isna(interaction_pval)
                else False,
                "interpretation": (
                    "Pre-trends differ significantly (parallel trends violated)"
                    if interaction_pval < SIGNIFICANCE_LEVEL
                    else "Pre-trends do not differ significantly (parallel trends plausible)"
                ),
            }

            return result

        except Exception as e:
            logger.error("Failed to run pre-trend test: %s", e)
            return {"error": str(e)}

    def _analyze_rent_divergence(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyze how rental prices diverge in pre-treatment period."""
        # Define pre-treatment period
        first_treatment = df.loc[df["treated"] == 1, "month"].min()

        if pd.isna(first_treatment):
            return pd.DataFrame()

        pre_period = df[df["month"] < first_treatment].copy()

        if "ever_treated" not in pre_period.columns:
            pre_period["ever_treated"] = pre_period["tract_geoid"].map(
                df.groupby("tract_geoid")["treated"].max()
            )

        # Calculate monthly average rent by treatment group
        monthly_avg = (
            pre_period.groupby(["month", "ever_treated"])["rental_price"]
            .mean()
            .reset_index()
        )

        # Pivot to get treated and control in separate columns
        monthly_avg = monthly_avg.pivot_table(
            index="month", columns="ever_treated", values="rental_price"
        ).reset_index()

        monthly_avg.columns = ["month", "control_rent", "treated_rent"]

        # Calculate gap
        monthly_avg["gap"] = monthly_avg["treated_rent"] - monthly_avg["control_rent"]
        monthly_avg["pct_gap"] = monthly_avg["gap"] / monthly_avg["control_rent"] * 100

        return monthly_avg

    def _check_covariate_balance(self, df: pd.DataFrame) -> dict[str, Any]:
        """Check covariate balance and compute standardized differences."""
        comparison = self._compare_tract_characteristics(df)

        if comparison.empty:
            return {"error": "No covariates available"}

        # Rule of thumb: |standardized difference| > 0.1 indicates imbalance
        imbalanced = comparison[abs(comparison["cohens_d"]) > BALANCE_THRESHOLD]

        balance_summary = {
            "n_covariates": len(comparison),
            "n_imbalanced": len(imbalanced),
            "max_imbalance": comparison["cohens_d"].abs().max()
            if not comparison.empty
            else np.nan,
            "imbalanced_covariates": imbalanced["covariate"].tolist()
            if not imbalanced.empty
            else [],
            "balance_assessment": (
                "Good balance (all |d| < 0.1)"
                if len(imbalanced) == 0
                else f"Poor balance ({len(imbalanced)}/{len(comparison)} covariates imbalanced)"
            ),
        }

        return balance_summary

    def _log_diagnostic_summary(
        self,
        comparison: pd.DataFrame,
        pretrend_test: dict[str, Any],
        divergence: pd.DataFrame,
    ) -> None:
        """Log summary of diagnostic findings."""
        logger.info("=" * 60)
        logger.info("PRE-TREND DIAGNOSTIC SUMMARY")
        logger.info("=" * 60)

        # 1. Covariate differences
        if not comparison.empty:
            logger.info("\n1. TRACT CHARACTERISTICS (Treated vs. Control):")
            significant_diffs = comparison[comparison["significant"]]
            if not significant_diffs.empty:
                logger.info("   Significant differences found:")
                for _, row in significant_diffs.iterrows():
                    logger.info(
                        "   - %s: Treated=%.2f, Control=%.2f, Diff=%.2f (%.1f%%), p=%.4f",
                        row["covariate"],
                        row["treated_mean"],
                        row["control_mean"],
                        row["difference"],
                        row["pct_difference"],
                        row["p_value"],
                    )
            else:
                logger.info("   No significant differences found")

        # 2. Pre-trend test
        if "error" not in pretrend_test:
            logger.info("\n2. PARALLEL TRENDS TEST (Pre-treatment):")
            logger.info(
                "   Interaction coefficient: %.4f (SE=%.4f, p=%.4f)",
                pretrend_test.get("interaction_coef", np.nan),
                pretrend_test.get("interaction_se", np.nan),
                pretrend_test.get("p_value", np.nan),
            )
            logger.info("   %s", pretrend_test.get("interpretation", ""))

        # 3. Rent gap trends
        if not divergence.empty:
            logger.info("\n3. PRE-TREATMENT RENT GAP:")
            first_gap = divergence.iloc[0]["gap"]
            last_gap = divergence.iloc[-1]["gap"]
            gap_change = last_gap - first_gap
            logger.info("   Initial gap: $%.2f", first_gap)
            logger.info("   Final gap: $%.2f", last_gap)
            logger.info(
                "   Change: $%.2f (%s)",
                gap_change,
                "widening" if gap_change > 0 else "narrowing",
            )

        logger.info("=" * 60)
