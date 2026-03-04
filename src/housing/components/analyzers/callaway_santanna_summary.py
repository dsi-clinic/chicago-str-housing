"""Summary analyzer for Callaway & Sant'Anna (2020) ATTs.

This component takes the detailed group-time ATT estimates produced by
`CallawaySantAnnaAnalyzer` and collapses them to:

1. The existing overall ATT for the full sample (already in context as
   `cs_overall_att`, computed by `CallawaySantAnnaAnalyzer`)
2. A cohort-level overall ATT for each treatment cohort, averaging over all
   available post-treatment periods for that cohort.

For each cohort, we report:
    - Overall ATT (level effect, in dollars)
    - Standard error of that overall ATT
    - 95% confidence interval
    - Number of post-treatment periods used
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class CallawaySantAnnaSummaryAnalyzer(Analyzer):
    """Summarize overall and cohort-level ATTs from Callaway & Sant'Anna."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize the summary analyzer.

        Args:
            output_dir: Optional directory for saving tabular ATT summaries.
                        Defaults to `/project/output`.
        """
        super().__init__(
            "callaway_santanna_att_summary",
            "Summarize overall and cohort-level ATT from Callaway & Sant'Anna",
        )
        # cs_group_time_atts is required; cs_cohort_dynamics is used for
        # pre-treatment significance checks when available.
        self.required_data = ["cs_group_time_atts"]
        self.output_dir = Path(output_dir or "/project/output")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Compute an overall ATT per cohort, plus standard errors and CIs.

        Expected context keys (from `CallawaySantAnnaAnalyzer`):
            - cs_group_time_atts: DataFrame with columns
                ['cohort', 'time', 'rel_time', 'att', 'se',
                 'n_treated', 'n_control']
            - cs_overall_att: dict with keys
                ['att', 'se', 'ci_low', 'ci_high', 'p_value']
        """
        group_time_atts = context.get("cs_group_time_atts")

        if group_time_atts is None or not isinstance(group_time_atts, pd.DataFrame):
            logger.warning(
                "cs_group_time_atts not found or not a DataFrame in context; "
                "skipping Callaway-Sant'Anna ATT summary."
            )
            return {
                "cs_overall_att_by_cohort": pd.DataFrame(),
            }

        if group_time_atts.empty:
            logger.warning(
                "cs_group_time_atts DataFrame is empty; "
                "no cohort-level ATT summary can be computed."
            )
            return {
                "cs_overall_att_by_cohort": pd.DataFrame(),
            }

        logger.info("Computing cohort-level overall ATTs from Callaway & Sant'Anna...")

        overall_att = context.get("cs_overall_att")
        cohort_summary = self._compute_overall_by_cohort(group_time_atts)
        self._log_summary(
            cohort_summary=cohort_summary,
            overall_att=overall_att,
        )

        # Build and persist a clean tabular summary (overall + cohorts)
        summary_table = self._build_summary_table(
            cohort_summary=cohort_summary,
            overall_att=overall_att,
        )
        summary_path = self._write_summary_table(summary_table)

        # Compute and persist pre-treatment significance counts by cohort
        sig_counts = self._compute_pretrend_significance(context)
        sig_counts_path = self._write_sig_counts_table(sig_counts)

        return {
            # Existing overall ATT for the full sample is left untouched
            # in context as `cs_overall_att`.
            "cs_overall_att_by_cohort": cohort_summary,
            "cs_att_summary_table": summary_table,
            "cs_att_summary_path": str(summary_path) if summary_path is not None else None,
            "cs_pretrend_sig_counts": sig_counts,
            "cs_pretrend_sig_counts_path": str(sig_counts_path) if sig_counts_path is not None else None,
        }

    def _compute_overall_by_cohort(
        self,
        group_time_atts: pd.DataFrame,
    ) -> pd.DataFrame:
        """Collapse ATT(g,t) to a single post-treatment ATT per cohort.

        For each cohort g, we take all post-treatment relative times (rel_time >= 0)
        for which ATT(g,t) is available and compute a weighted average:

            ATT_g = sum_w w_t * ATT(g, t)

        where weights w_t are proportional to the number of treated units in the
        cohort-period cell (n_treated). Since n_treated is constant within a cohort,
        this reduces to an equal-weighted average across post-treatment periods.

        The standard error of ATT_g is aggregated conservatively assuming
        independence across periods:

            se_g = sqrt( sum_t (w_t^2 * se(g,t)^2) )
        """
        # Keep only post-treatment periods
        post = group_time_atts[group_time_atts["rel_time"] >= 0].copy()

        if post.empty:
            return pd.DataFrame(
                columns=[
                    "cohort",
                    "att",
                    "se",
                    "ci_low",
                    "ci_high",
                    "p_value",
                    "n_periods",
                    "n_treated",
                ]
            )

        summaries: list[dict[str, Any]] = []

        for cohort, cohort_df in post.groupby("cohort"):
            cohort_df = cohort_df.dropna(subset=["att", "se"])
            if cohort_df.empty:
                continue

            # Weights based on number of treated units
            weights = cohort_df["n_treated"].to_numpy(dtype=float)
            if np.any(weights < 0):
                raise ValueError("n_treated must be non-negative for all rows.")

            if np.all(weights == 0):
                # Fallback: equal weights if somehow all n_treated are zero
                weights = np.ones(len(cohort_df), dtype=float)

            weights = weights / weights.sum()

            att_vals = cohort_df["att"].to_numpy(dtype=float)
            se_vals = cohort_df["se"].to_numpy(dtype=float)

            att_g = float(np.sum(att_vals * weights))
            se_g = float(np.sqrt(np.sum((se_vals**2) * (weights**2))))

            if se_g > 0:
                z_score = att_g / se_g
                p_value = float(2 * (1 - stats.norm.cdf(abs(z_score))))
            else:
                p_value = float("nan")

            ci_low = att_g - 1.96 * se_g
            ci_high = att_g + 1.96 * se_g

            summaries.append(
                {
                    "cohort": cohort,
                    "att": att_g,
                    "se": se_g,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "p_value": p_value,
                    "n_periods": int(len(cohort_df)),
                    # Cohort size is constant across periods; take the max as a proxy
                    "n_treated": int(cohort_df["n_treated"].max()),
                }
            )

        if not summaries:
            return pd.DataFrame(
                columns=[
                    "cohort",
                    "att",
                    "se",
                    "ci_low",
                    "ci_high",
                    "p_value",
                    "n_periods",
                    "n_treated",
                ]
            )

        summary_df = pd.DataFrame(summaries)
        # Sort by cohort calendar time for readability
        if pd.api.types.is_datetime64_any_dtype(summary_df["cohort"]):
            summary_df = summary_df.sort_values("cohort")

        return summary_df.reset_index(drop=True)

    def _log_summary(
        self,
        cohort_summary: pd.DataFrame,
        overall_att: dict[str, Any] | None,
    ) -> None:
        """Log overall and cohort-level ATT summaries."""
        logger.info("\n=== Callaway-Sant'Anna ATT Summary ===")

        if overall_att:
            att = overall_att.get("att", float("nan"))
            se = overall_att.get("se", float("nan"))
            ci_low = overall_att.get("ci_low", float("nan"))
            ci_high = overall_att.get("ci_high", float("nan"))
            p_val = overall_att.get("p_value", float("nan"))

            logger.info("\nOverall ATT (full sample, post-treatment):")
            logger.info("  ATT: $%.2f", att)
            logger.info("  SE: $%.2f", se)
            logger.info("  95%% CI: [$%.2f, $%.2f]", ci_low, ci_high)
            logger.info("  P-value: %.4f", p_val)

        if cohort_summary is None or cohort_summary.empty:
            logger.info("\nNo cohort-level ATT summaries available.")
            return

        logger.info("\nCohort-level overall ATTs (post-treatment):")
        for _, row in cohort_summary.iterrows():
            cohort = row["cohort"]
            att = row["att"]
            se = row["se"]
            ci_low = row["ci_low"]
            ci_high = row["ci_high"]
            p_val = row["p_value"]
            n_periods = row["n_periods"]
            n_treated = row["n_treated"]

            cohort_label = str(cohort)[:10]
            logger.info(
                "  Cohort %s: ATT=$%.2f (SE=$%.2f, 95%% CI=[$%.2f, $%.2f], "
                "p=%.4f, periods=%d, n_treated=%d)",
                cohort_label,
                att,
                se,
                ci_low,
                ci_high,
                p_val,
                n_periods,
                n_treated,
            )
    def _build_summary_table(
        self,
        cohort_summary: pd.DataFrame,
        overall_att: dict[str, Any] | None,
    ) -> pd.DataFrame:
        """Create a single tidy table with overall and cohort-level ATTs."""
        rows: list[dict[str, Any]] = []

        # Overall ATT row (if available)
        if overall_att:
            rows.append(
                {
                    "level": "overall",
                    "cohort": None,
                    "att": overall_att.get("att", np.nan),
                    "se": overall_att.get("se", np.nan),
                    "ci_low": overall_att.get("ci_low", np.nan),
                    "ci_high": overall_att.get("ci_high", np.nan),
                    "p_value": overall_att.get("p_value", np.nan),
                    # These are not uniquely defined for the overall ATT, so leave blank
                    "n_periods": np.nan,
                    "n_treated": np.nan,
                }
            )

        # Cohort-level rows
        if cohort_summary is not None and not cohort_summary.empty:
            for _, row in cohort_summary.iterrows():
                rows.append(
                    {
                        "level": "cohort",
                        "cohort": row.get("cohort"),
                        "att": row.get("att", np.nan),
                        "se": row.get("se", np.nan),
                        "ci_low": row.get("ci_low", np.nan),
                        "ci_high": row.get("ci_high", np.nan),
                        "p_value": row.get("p_value", np.nan),
                        "n_periods": row.get("n_periods", np.nan),
                        "n_treated": row.get("n_treated", np.nan),
                    }
                )

        if not rows:
            return pd.DataFrame(
                columns=[
                    "level",
                    "cohort",
                    "att",
                    "se",
                    "ci_low",
                    "ci_high",
                    "p_value",
                    "n_periods",
                    "n_treated",
                ]
            )

        return pd.DataFrame(rows)

    def _write_summary_table(self, summary_table: pd.DataFrame) -> Path | None:
        """Write the ATT summary table to a CSV file in the output directory."""
        if summary_table is None or summary_table.empty:
            logger.info(
                "ATT summary table is empty; no CSV file will be written for "
                "Callaway-Sant'Anna ATT summary."
            )
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / "did_cs_att_summary.csv"

        summary_table.to_csv(output_path, index=False)
        logger.info(
            "Callaway-Sant'Anna ATT summary table written to: %s",
            output_path,
        )

        return output_path

    def _compute_pretrend_significance(self, context: dict[str, Any]) -> pd.DataFrame:
        """Compute, for each cohort, how many pre-treatment CS coefficients are significant.

        We use the cohort-specific dynamic effects from `cs_cohort_dynamics` and
        count, for each cohort, how many pre-treatment relative times have 95% CIs
        that exclude 0 (i.e., evidence of pre-trend violations).

        By default we treat relative times -12, ..., -2 as "pre-treatment" and
        exclude -1 because it is the reference period in the event study.
        """
        cohort_dyn = context.get("cs_cohort_dynamics")
        if cohort_dyn is None or not isinstance(cohort_dyn, pd.DataFrame) or cohort_dyn.empty:
            logger.info(
                "cs_cohort_dynamics not available or empty; "
                "skipping pre-treatment significance counts."
            )
            return pd.DataFrame(
                columns=["cohort", "n_pre_periods", "n_significant_pre_coefs"]
            )

        # 11 pre-treatment periods: rel_time -12, ..., -2
        pre_times = list(range(-12, -1))
        pre_dyn = cohort_dyn[cohort_dyn["rel_time"].isin(pre_times)].copy()

        if pre_dyn.empty:
            logger.info(
                "No pre-treatment periods found in cs_cohort_dynamics for rel_time -12..-2."
            )
            return pd.DataFrame(
                columns=["cohort", "n_pre_periods", "n_significant_pre_coefs"]
            )

        # A coefficient is significant if its 95% CI does not cross 0
        pre_dyn["significant"] = (pre_dyn["ci_low"] > 0) | (pre_dyn["ci_high"] < 0)

        sig_counts = (
            pre_dyn.groupby("cohort")
            .agg(
                n_pre_periods=("rel_time", "size"),
                n_significant_pre_coefs=("significant", "sum"),
            )
            .reset_index()
        )

        logger.info("Computed pre-treatment significance counts for %d cohorts.", len(sig_counts))
        return sig_counts

    def _write_sig_counts_table(self, sig_counts: pd.DataFrame) -> Path | None:
        """Write pre-treatment significance counts to CSV in the output directory."""
        if sig_counts is None or sig_counts.empty:
            logger.info(
                "Pre-treatment significance table is empty; "
                "no CSV file will be written."
            )
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / "did_cs_pretrend_significance.csv"

        sig_counts.to_csv(output_path, index=False)
        logger.info(
            "Callaway-Sant'Anna pre-treatment significance table written to: %s",
            output_path,
        )

        return output_path


