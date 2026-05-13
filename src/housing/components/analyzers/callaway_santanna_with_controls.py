"""Callaway & Sant'Anna estimator with covariate adjustment.

Extends the basic CS estimator to include:
1. Time-invariant covariates (census characteristics, baseline rent)
2. Tract-specific linear time trends (to handle differential trends)

**Estimation methods (per Sant'Anna & Zhao 2020):**

1. **Outcome regression (or)**: Residualize Y on covariates before computing DiD
2. **Inverse probability weighting (ipw)**: Weight comparison tracts by propensity score
3. **Doubly robust (dr)**: Combine both methods (default, recommended by CS 2021)

**Tract-specific trends:**

Including tract-specific linear trends allows for mild violations of parallel trends
where treated and control groups have different baseline growth rates, as long as
the difference is linear. Trends are estimated using pre-treatment data only to
avoid contamination from treatment effects.
"""

import logging
from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.linear_model import LogisticRegression

from housing.components.analyzers.callaway_santanna_pretrend_test import (
    compute_pre_trend_joint_test_from_cs_event_study,
)
from pipeline.base import Analyzer

# Default covariates for propensity score / outcome regression
DEFAULT_COVARIATES = [
    "median_income",
    "median_house_value",
    "baseline_rent",
    "pct_bachelor",
    "pct_rented",
    "median_age",
    "total_population",
]

logger = logging.getLogger(__name__)

# Constants
MAX_PRE_TIME = 12  # Maximum pre-treatment periods
MAX_POST_TIME = 36  # Maximum post-treatment periods


class CallawaySantAnnaWithControlsAnalyzer(Analyzer):
    """CS estimator with covariate adjustment and tract-specific trends."""

    def __init__(
        self,
        comparison_group: str = "nevertreated",
        anticipation: int = 0,
        min_cohort_size: int = 10,
        include_covariates: bool = True,
        include_tract_trends: bool = True,
        covariates: list[str] | None = None,
        estimation_method: str = "dr",
    ) -> None:
        """Initialize the enhanced CS analyzer.

        Args:
            comparison_group: "nevertreated" or "notyettreated"
            anticipation: Periods before treatment with potential anticipation effects
            min_cohort_size: Minimum cohort size for stable estimation
            include_covariates: Whether to adjust for time-invariant covariates
            include_tract_trends: Whether to include tract-specific linear time trends
            covariates: List of covariate names to include (None = use defaults)
            estimation_method: "dr" (doubly robust, default), "ipw", or "or" (outcome regression)
        """
        super().__init__(
            "callaway_santanna_with_controls",
            "Callaway & Sant'Anna with covariate adjustment and tract trends",
        )
        if estimation_method not in ("dr", "ipw", "or"):
            raise ValueError(
                f"estimation_method must be 'dr', 'ipw', or 'or', got '{estimation_method}'"
            )
        self.comparison_group = comparison_group
        self.anticipation = anticipation
        self.min_cohort_size = min_cohort_size
        self.include_covariates = include_covariates
        self.include_tract_trends = include_tract_trends
        self.covariates = covariates
        self.estimation_method = estimation_method
        self._propensity_diagnostics: list[dict] = []

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Estimate group-time ATTs with covariate adjustment."""
        logger.info("Starting Callaway & Sant'Anna with controls...")
        logger.info("Comparison group: %s", self.comparison_group)
        logger.info("Estimation method: %s", self.estimation_method)
        logger.info("Include covariates: %s", self.include_covariates)
        logger.info("Include tract trends: %s", self.include_tract_trends)
        self._propensity_diagnostics = []

        # Prefer the panel with covariates; fall back to base panel
        did_panel = context.get("did_panel_with_covariates")
        if did_panel is None:
            did_panel = context.get("did_panel")
        if did_panel is None:
            logger.error("did_panel not found in context")
            raise ValueError("did_panel not found in context")

        panel = did_panel.copy()
        panel = panel.dropna(subset=["rental_price"]).reset_index(drop=True)

        # Residualize outcome if using controls
        if self.include_covariates or self.include_tract_trends:
            panel = self._residualize_outcome(panel, context)

        # Standard CS estimation on (residualized) outcome
        cohort_info = self._identify_cohorts(panel)
        logger.info(
            "Identified %d treatment cohorts and %d never-treated tracts",
            len(cohort_info["treated_cohorts"]),
            cohort_info["n_never_treated"],
        )

        group_time_atts = self._estimate_group_time_atts(panel, cohort_info)
        logger.info("Estimated %d group-time ATTs", len(group_time_atts))

        event_study_agg = self._aggregate_to_event_study(group_time_atts, panel)
        logger.info(
            "Aggregated to event study with %d relative time periods",
            len(event_study_agg),
        )

        overall_att = self._compute_overall_att(group_time_atts)
        logger.info(
            "Overall ATT: %.2f (SE: %.2f)", overall_att["att"], overall_att["se"]
        )

        cohort_dynamics = self._compute_cohort_dynamics(group_time_atts)

        pre_trend = compute_pre_trend_joint_test_from_cs_event_study(event_study_agg)

        # Write to distinct keys so basic CS results are not overwritten
        return {
            "cs_group_time_atts_with_controls": group_time_atts,
            "cs_event_study_with_controls": event_study_agg,
            "cs_overall_att_with_controls": overall_att,
            "cs_cohort_dynamics_with_controls": cohort_dynamics,
            "cs_cohort_info_with_controls": cohort_info,
            "cs_comparison_group": self.comparison_group,
            "cs_with_controls": True,
            "cs_include_covariates": self.include_covariates,
            "cs_include_tract_trends": self.include_tract_trends,
            "cs_estimation_method": self.estimation_method,
            "cs_propensity_diagnostics": self._propensity_diagnostics,
            "cs_pre_trend_joint_test_with_controls": pre_trend["summary"],
            "cs_pre_trend_joint_test_periods_with_controls": pre_trend["periods"],
        }

    def _residualize_outcome(
        self, df: pd.DataFrame, _context: dict[str, Any]
    ) -> pd.DataFrame:
        """Residualize rental_price on covariates and/or tract trends.

        IMPORTANT: Only fits on pre-treatment data to avoid treatment effects
        contaminating the trend estimates. For treated tracts, pre-treatment means
        months before their first treatment. For never-treated tracts, all months
        are used.
        """
        logger.info("Residualizing outcome on controls (pre-treatment fit only)...")

        # --- Build pre-treatment mask ---
        # For each treated tract, find its first treatment month
        tract_first_treatment = (
            df[df["treated"] == 1].groupby("tract_geoid")["month"].min()
        )
        # Map each row to its tract's first treatment month (NaT for never-treated)
        df["_first_treat"] = df["tract_geoid"].map(tract_first_treatment)
        # Pre-treatment: never-treated tracts (NaT) OR month < first treatment
        pre_treatment_mask = df["_first_treat"].isna() | (
            df["month"] < df["_first_treat"]
        )
        logger.info(
            "  Pre-treatment observations: %d / %d (%.1f%%)",
            pre_treatment_mask.sum(),
            len(df),
            100 * pre_treatment_mask.mean(),
        )

        # --- Build control matrix ---
        X_components = []

        if self.include_covariates:
            covariate_list = self.covariates or DEFAULT_COVARIATES

            covariate_data = pd.DataFrame(index=df.index)
            for cov in covariate_list:
                if cov in df.columns and df[cov].notna().sum() > 0:
                    cov_std = df[cov].std()
                    if cov_std > 0:
                        covariate_data[cov] = (df[cov] - df[cov].mean()) / cov_std
                        logger.info("  Added covariate: %s", cov)

            if not covariate_data.empty:
                X_components.append(covariate_data)

        if self.include_tract_trends:
            logger.info("  Adding tract-specific linear time trends")
            df["time_index"] = (
                (df["month"] - df["month"].min()).dt.days / 30.44
            ).astype(int)

            tract_dummies = pd.get_dummies(
                df["tract_geoid"], prefix="tract", drop_first=True
            )
            tract_trends = tract_dummies.multiply(df["time_index"], axis=0)
            tract_trends.columns = [col + "_trend" for col in tract_trends.columns]
            X_components.append(tract_trends)

        if not X_components:
            logger.warning("No controls to residualize on")
            return df.drop(columns=["_first_treat"])

        # --- Fit on pre-treatment data only, predict for full panel ---
        y_full = df["rental_price"].to_numpy()
        X_full = pd.concat(X_components, axis=1)
        # Fill NaN covariates with 0 (covariates are standardized, so 0 = mean)
        n_nan = X_full.isna().sum().sum()
        if n_nan > 0:
            logger.info(
                "  Filling %d NaN values in design matrix with 0 (mean-imputed)",
                n_nan,
            )
            X_full = X_full.fillna(0)
        X_full = sm.add_constant(X_full, has_constant="add")

        X_pre = X_full.loc[pre_treatment_mask]
        y_pre = y_full[pre_treatment_mask.to_numpy()]

        try:
            model = sm.OLS(y_pre, X_pre).fit()
            predicted_full = model.predict(X_full)

            df["rental_price_original"] = df["rental_price"]
            original_mean = df["rental_price"].mean()
            df["rental_price"] = y_full - predicted_full + original_mean

            logger.info(
                "Residualized outcome (pre-treatment fit): R² = %.4f, %d controls, %d pre-obs",
                model.rsquared,
                X_pre.shape[1] - 1,
                len(X_pre),
            )
        except Exception as e:
            logger.warning("Residualization failed: %s. Using original outcome.", e)

        return df.drop(columns=["_first_treat"])

    def _identify_cohorts(self, df: pd.DataFrame) -> dict[str, Any]:
        """Identify treatment cohorts and never-treated units."""
        tract_first_treatment = (
            df[df["treated"] == 1]
            .groupby("tract_geoid")["month"]
            .min()
            .reset_index()
            .rename(columns={"month": "first_treatment_month"})
        )

        treated_tracts = tract_first_treatment["tract_geoid"].unique()
        all_tracts = df["tract_geoid"].unique()
        never_treated_tracts = set(all_tracts) - set(treated_tracts)

        cohort_sizes = tract_first_treatment.groupby("first_treatment_month").size()
        cohort_sizes = cohort_sizes[cohort_sizes >= self.min_cohort_size]

        cohorts_df = tract_first_treatment[
            tract_first_treatment["first_treatment_month"].isin(cohort_sizes.index)
        ]

        logger.info("Cohort summary:")
        for cohort_date, size in cohort_sizes.items():
            logger.info("  Cohort %s: %d tracts", str(cohort_date)[:10], size)

        return {
            "treated_cohorts": cohorts_df,
            "never_treated_tracts": list(never_treated_tracts),
            "n_never_treated": len(never_treated_tracts),
            "cohort_sizes": cohort_sizes,
        }

    def _estimate_group_time_atts(
        self, df: pd.DataFrame, cohort_info: dict[str, Any]
    ) -> pd.DataFrame:
        """Estimate ATT(g,t) for each cohort g and time period t."""
        cohorts_df = cohort_info["treated_cohorts"]
        never_treated = cohort_info["never_treated_tracts"]

        results = []

        cohorts = sorted(cohorts_df["first_treatment_month"].unique())
        time_periods = sorted(df["month"].unique())

        for cohort_date in cohorts:
            cohort_tracts = cohorts_df[
                cohorts_df["first_treatment_month"] == cohort_date
            ]["tract_geoid"].to_numpy()

            logger.debug(
                "Processing cohort %s with %d tracts",
                str(cohort_date)[:10],
                len(cohort_tracts),
            )

            base_period = cohort_date - pd.DateOffset(months=1)

            for t in time_periods:
                if t == base_period:
                    continue

                if self.comparison_group == "nevertreated":
                    comparison_tracts = never_treated
                elif self.comparison_group == "notyettreated":
                    not_yet_treated = cohorts_df[
                        cohorts_df["first_treatment_month"] > t
                    ]["tract_geoid"].to_numpy()
                    comparison_tracts = list(set(never_treated) | set(not_yet_treated))
                else:
                    raise ValueError(
                        f"Unknown comparison_group: {self.comparison_group}"
                    )

                if len(comparison_tracts) == 0:
                    logger.warning(
                        "No comparison units for cohort %s at time %s", cohort_date, t
                    )
                    continue

                att_result = self._estimate_single_att(
                    df=df,
                    cohort_tracts=cohort_tracts,
                    comparison_tracts=comparison_tracts,
                    cohort_date=cohort_date,
                    current_date=t,
                )

                if att_result is not None:
                    months_diff = (t.year - cohort_date.year) * 12 + (
                        t.month - cohort_date.month
                    )

                    results.append(
                        {
                            "cohort": cohort_date,
                            "time": t,
                            "rel_time": months_diff,
                            "att": att_result["att"],
                            "se": att_result["se"],
                            "n_treated": len(cohort_tracts),
                            "n_control": len(comparison_tracts),
                        }
                    )

        return pd.DataFrame(results)

    def _compute_first_differences(
        self,
        df: pd.DataFrame,
        tract_ids: list | np.ndarray,
        current_date: pd.Timestamp,
        pre_period: pd.Timestamp,
    ) -> pd.DataFrame | None:
        """Compute ΔY_i = Y_{i,t} - Y_{i,g-1} for a set of tracts.

        Returns a DataFrame indexed by tract_geoid with column 'change',
        or None if insufficient data.
        """
        sub = df[
            (df["tract_geoid"].isin(tract_ids))
            & (df["month"].isin([current_date, pre_period]))
        ][["tract_geoid", "month", "rental_price"]]

        pivoted = sub.pivot_table(
            index="tract_geoid", columns="month", values="rental_price", aggfunc="first"
        )
        if current_date not in pivoted.columns or pre_period not in pivoted.columns:
            return None

        pivoted["change"] = pivoted[current_date] - pivoted[pre_period]
        pivoted = pivoted.dropna(subset=["change"])
        if pivoted.empty:
            return None
        return pivoted[["change"]]

    def _get_tract_covariates(
        self, df: pd.DataFrame, tract_ids: Iterable[Any]
    ) -> pd.DataFrame:
        """Get time-invariant covariates for a set of tracts (one row per tract)."""
        covariate_list = self.covariates or DEFAULT_COVARIATES
        available = [c for c in covariate_list if c in df.columns]
        if not available:
            return pd.DataFrame(index=pd.Index(tract_ids, name="tract_geoid"))

        tract_covs = df.groupby("tract_geoid")[available].first()
        tract_covs = tract_covs.loc[tract_covs.index.isin(tract_ids)]

        # Standardize each column
        for col in available:
            std = tract_covs[col].std()
            if std > 0:
                tract_covs[col] = (tract_covs[col] - tract_covs[col].mean()) / std
            else:
                tract_covs = tract_covs.drop(columns=[col])

        return tract_covs.dropna()

    def _estimate_single_att(
        self,
        df: pd.DataFrame,
        cohort_tracts: np.ndarray,
        comparison_tracts: list,
        cohort_date: pd.Timestamp,
        current_date: pd.Timestamp,
    ) -> dict[str, float] | None:
        """Estimate a single ATT(g,t), dispatching by estimation_method."""
        pre_period = cohort_date - pd.DateOffset(months=1)

        # Compute first differences for both groups
        treated_diff = self._compute_first_differences(
            df, cohort_tracts, current_date, pre_period
        )
        control_diff = self._compute_first_differences(
            df, comparison_tracts, current_date, pre_period
        )

        if treated_diff is None or control_diff is None:
            return None
        if len(treated_diff) == 0 or len(control_diff) == 0:
            return None

        if self.estimation_method == "or":
            return self._estimate_att_or(treated_diff, control_diff)

        # For DR and IPW we need covariates
        all_tract_ids = list(treated_diff.index) + list(control_diff.index)
        covariates = self._get_tract_covariates(df, all_tract_ids)

        # Fallback to OR if not enough covariates or tracts
        n_covs = covariates.shape[1] if not covariates.empty else 0
        n_total = len(treated_diff) + len(control_diff)
        if n_covs == 0 or n_total < 2 * n_covs:
            logger.debug("Falling back to OR: n_covs=%d, n_total=%d", n_covs, n_total)
            return self._estimate_att_or(treated_diff, control_diff)

        if self.estimation_method == "ipw":
            return self._estimate_att_ipw(treated_diff, control_diff, covariates)

        # Default: doubly robust
        return self._estimate_att_dr(treated_diff, control_diff, covariates)

    def _estimate_att_or(
        self,
        treated_diff: pd.DataFrame,
        control_diff: pd.DataFrame,
    ) -> dict[str, float]:
        """Outcome regression only — simple DiD (original behavior)."""
        att = treated_diff["change"].mean() - control_diff["change"].mean()

        treated_var = treated_diff["change"].var()
        control_var = control_diff["change"].var()
        n_treated = len(treated_diff)
        n_control = len(control_diff)

        se = np.sqrt(treated_var / n_treated + control_var / n_control)
        return {"att": att, "se": se}

    def _estimate_att_ipw(
        self,
        treated_diff: pd.DataFrame,
        control_diff: pd.DataFrame,
        covariates: pd.DataFrame,
    ) -> dict[str, float]:
        """Inverse probability weighting estimator."""
        treated_ids = set(treated_diff.index)
        control_ids = set(control_diff.index)

        # Align covariates with tracts that have valid diffs
        valid_ids = (treated_ids | control_ids) & set(covariates.index)
        treated_ids = treated_ids & valid_ids
        control_ids = control_ids & valid_ids

        if len(treated_ids) == 0 or len(control_ids) == 0:
            return self._estimate_att_or(treated_diff, control_diff)

        all_ids = sorted(treated_ids | control_ids)
        X = covariates.loc[all_ids].to_numpy()
        D = np.array([1 if tid in treated_ids else 0 for tid in all_ids])

        # Fit propensity score
        try:
            lr = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs")
            lr.fit(X, D)
            p_hat = lr.predict_proba(X)[:, 1]
        except Exception:
            logger.debug("Logistic regression failed, falling back to OR")
            return self._estimate_att_or(treated_diff, control_diff)

        # Trim propensity scores
        p_hat = np.clip(p_hat, 0.01, 0.99)

        # Build arrays aligned to all_ids
        delta_y = np.array(
            [
                treated_diff.loc[tid, "change"]
                if tid in treated_ids
                else control_diff.loc[tid, "change"]
                for tid in all_ids
            ]
        )

        # IPW weights for comparison units
        treated_mask = D == 1
        control_mask = D == 0

        odds = p_hat[control_mask] / (1.0 - p_hat[control_mask])
        if odds.sum() == 0:
            logger.debug("All-zero IPW weights, falling back to OR")
            return self._estimate_att_or(treated_diff, control_diff)
        w = odds / odds.sum()

        n_g = treated_mask.sum()
        att = (delta_y[treated_mask].sum() / n_g) - np.dot(w, delta_y[control_mask])

        # Influence-function SE
        p_g = n_g / len(D)
        influence = np.zeros(len(D))
        influence[treated_mask] = (1.0 / p_g) * (delta_y[treated_mask] - att)
        w_full = np.zeros(len(D))
        w_full[control_mask] = w
        influence[control_mask] = -w_full[control_mask] * delta_y[control_mask] / p_g
        se = np.sqrt(np.mean(influence**2) / len(D))

        # Record diagnostics
        self._propensity_diagnostics.append(
            {
                "p_hat_mean": float(p_hat.mean()),
                "p_hat_min": float(p_hat.min()),
                "p_hat_max": float(p_hat.max()),
                "n_treated": int(n_g),
                "n_control": int(control_mask.sum()),
            }
        )

        return {"att": att, "se": se}

    def _estimate_att_dr(
        self,
        treated_diff: pd.DataFrame,
        control_diff: pd.DataFrame,
        covariates: pd.DataFrame,
    ) -> dict[str, float]:
        """Doubly robust DiD estimator (Sant'Anna & Zhao 2020)."""
        treated_ids = set(treated_diff.index)
        control_ids = set(control_diff.index)

        # Align covariates with tracts that have valid diffs
        valid_ids = (treated_ids | control_ids) & set(covariates.index)
        treated_ids = treated_ids & valid_ids
        control_ids = control_ids & valid_ids

        if len(treated_ids) == 0 or len(control_ids) == 0:
            return self._estimate_att_or(treated_diff, control_diff)

        all_ids = sorted(treated_ids | control_ids)
        X = covariates.loc[all_ids].to_numpy()
        D = np.array([1 if tid in treated_ids else 0 for tid in all_ids])
        delta_y = np.array(
            [
                treated_diff.loc[tid, "change"]
                if tid in treated_ids
                else control_diff.loc[tid, "change"]
                for tid in all_ids
            ]
        )

        treated_mask = D == 1
        control_mask = D == 0
        n_g = int(treated_mask.sum())
        n = len(D)

        # --- Step 1: Propensity score ---
        try:
            lr = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs")
            lr.fit(X, D)
            p_hat = lr.predict_proba(X)[:, 1]
        except Exception:
            logger.debug("Logistic regression failed in DR, falling back to OR")
            return self._estimate_att_or(treated_diff, control_diff)

        p_hat = np.clip(p_hat, 0.01, 0.99)

        # --- Step 2: Outcome regression on comparison tracts ---
        X_control = X[control_mask]
        y_control = delta_y[control_mask]

        try:
            X_control_c = sm.add_constant(X_control, has_constant="add")
            or_model = sm.OLS(y_control, X_control_c).fit()
            X_all_c = sm.add_constant(X, has_constant="add")
            m_hat = or_model.predict(X_all_c)
        except Exception:
            logger.debug("OLS in DR failed, falling back to IPW")
            return self._estimate_att_ipw(treated_diff, control_diff, covariates)

        # --- Step 3: DR combination ---
        # IPW weights for comparison units
        odds = p_hat[control_mask] / (1.0 - p_hat[control_mask])
        if odds.sum() == 0:
            logger.debug("All-zero IPW weights in DR, falling back to OR")
            return self._estimate_att_or(treated_diff, control_diff)
        w = odds / odds.sum()

        # ATT_DR = mean over treated of [ΔY - m̂(X)] - weighted sum over control of [ΔY - m̂(X)]
        resid = delta_y - m_hat
        att = resid[treated_mask].mean() - np.dot(w, resid[control_mask])

        # --- Step 4: Influence function SE ---
        p_g = n_g / n
        w_full = np.zeros(n)
        w_full[control_mask] = w

        influence = np.zeros(n)
        influence[treated_mask] = (1.0 / p_g) * (resid[treated_mask] - att)
        influence[control_mask] = -w_full[control_mask] * resid[control_mask] / p_g
        se = np.sqrt(np.mean(influence**2) / n)

        # Record diagnostics
        self._propensity_diagnostics.append(
            {
                "p_hat_mean": float(p_hat.mean()),
                "p_hat_min": float(p_hat.min()),
                "p_hat_max": float(p_hat.max()),
                "n_treated": int(n_g),
                "n_control": int(control_mask.sum()),
            }
        )

        return {"att": att, "se": se}

    def _aggregate_to_event_study(
        self, group_time_atts: pd.DataFrame, df: pd.DataFrame
    ) -> pd.DataFrame:
        """Aggregate group-time ATTs to event study by relative time."""
        if group_time_atts.empty:
            return pd.DataFrame()

        rel_times = sorted(group_time_atts["rel_time"].unique())
        rel_times = [rt for rt in rel_times if -MAX_PRE_TIME <= rt <= MAX_POST_TIME]

        results = []

        for e in rel_times:
            atts_at_e = group_time_atts[group_time_atts["rel_time"] == e].copy()

            if atts_at_e.empty:
                continue

            weights = atts_at_e["n_treated"].to_numpy()
            weights = weights / weights.sum()

            agg_att = np.sum(atts_at_e["att"].to_numpy() * weights)
            agg_se = np.sqrt(np.sum((atts_at_e["se"].to_numpy() ** 2) * (weights**2)))

            ci_low = agg_att - 1.96 * agg_se
            ci_high = agg_att + 1.96 * agg_se

            results.append(
                {
                    "rel_time": e,
                    "att": agg_att,
                    "se": agg_se,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "n_cohorts": len(atts_at_e),
                }
            )

        event_study_df = pd.DataFrame(results).sort_values("rel_time")

        return event_study_df

    def _compute_overall_att(self, group_time_atts: pd.DataFrame) -> dict[str, float]:
        """Compute overall post-treatment ATT."""
        if group_time_atts.empty:
            return {"att": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan}

        post_treatment = group_time_atts[group_time_atts["rel_time"] >= 0].copy()

        if post_treatment.empty:
            return {"att": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan}

        weights = post_treatment["n_treated"].to_numpy()
        weights = weights / weights.sum()

        overall_att = np.sum(post_treatment["att"].to_numpy() * weights)
        overall_se = np.sqrt(
            np.sum((post_treatment["se"].to_numpy() ** 2) * (weights**2))
        )

        ci_low = overall_att - 1.96 * overall_se
        ci_high = overall_att + 1.96 * overall_se

        return {
            "att": overall_att,
            "se": overall_se,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "p_value": 2 * (1 - stats.norm.cdf(abs(overall_att / overall_se))),
        }

    def _compute_cohort_dynamics(self, group_time_atts: pd.DataFrame) -> pd.DataFrame:
        """Compute dynamic effects for each cohort separately."""
        if group_time_atts.empty:
            return pd.DataFrame()

        cohort_dynamics = []

        for cohort in group_time_atts["cohort"].unique():
            cohort_data = group_time_atts[group_time_atts["cohort"] == cohort].copy()
            cohort_data = cohort_data.sort_values("rel_time")

            for _, row in cohort_data.iterrows():
                cohort_dynamics.append(
                    {
                        "cohort": cohort,
                        "rel_time": row["rel_time"],
                        "att": row["att"],
                        "se": row["se"],
                        "ci_low": row["att"] - 1.96 * row["se"],
                        "ci_high": row["att"] + 1.96 * row["se"],
                    }
                )

        return pd.DataFrame(cohort_dynamics)
