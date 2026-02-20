"""Callaway & Sant'Anna estimator with covariate adjustment.

Extends the basic CS estimator to include:
1. Time-invariant covariates (census characteristics, baseline rent)
2. Tract-specific linear time trends (to handle differential trends)

**Covariate adjustment methods:**

1. **Outcome regression**: Residualize Y on covariates before computing DiD
2. **Inverse probability weighting**: Weight by propensity score
3. **Doubly robust**: Combine both methods

This implementation uses outcome regression for simplicity and interpretability.

**Tract-specific trends:**

Including tract-specific linear trends allows for mild violations of parallel trends
where treated and control groups have different baseline growth rates, as long as
the difference is linear.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

# Constants
MAX_PRE_TIME = 12   # Maximum pre-treatment periods
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
    ) -> None:
        """Initialize the enhanced CS analyzer.

        Args:
            comparison_group: "nevertreated" or "notyettreated"
            anticipation: Periods before treatment with potential anticipation effects
            min_cohort_size: Minimum cohort size for stable estimation
            include_covariates: Whether to adjust for time-invariant covariates
            include_tract_trends: Whether to include tract-specific linear time trends
            covariates: List of covariate names to include (None = use defaults)
        """
        super().__init__(
            "callaway_santanna_with_controls",
            "Callaway & Sant'Anna with covariate adjustment and tract trends",
        )
        self.comparison_group = comparison_group
        self.anticipation = anticipation
        self.min_cohort_size = min_cohort_size
        self.include_covariates = include_covariates
        self.include_tract_trends = include_tract_trends
        self.covariates = covariates

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Estimate group-time ATTs with covariate adjustment."""
        logger.info("Starting Callaway & Sant'Anna with controls...")
        logger.info("Comparison group: %s", self.comparison_group)
        logger.info("Include covariates: %s", self.include_covariates)
        logger.info("Include tract trends: %s", self.include_tract_trends)

        did_panel = context.get("did_panel")
        if did_panel is None:
            logger.error("did_panel not found in context")
            raise ValueError("did_panel not found in context")

        df = did_panel.copy()
        df = df.dropna(subset=["rental_price"]).reset_index(drop=True)

        # Residualize outcome if using controls
        if self.include_covariates or self.include_tract_trends:
            df = self._residualize_outcome(df, context)

        # Standard CS estimation on (residualized) outcome
        cohort_info = self._identify_cohorts(df)
        logger.info(
            "Identified %d treatment cohorts and %d never-treated tracts",
            len(cohort_info["treated_cohorts"]),
            cohort_info["n_never_treated"],
        )

        group_time_atts = self._estimate_group_time_atts(df, cohort_info)
        logger.info("Estimated %d group-time ATTs", len(group_time_atts))

        event_study_agg = self._aggregate_to_event_study(group_time_atts, df)
        logger.info(
            "Aggregated to event study with %d relative time periods",
            len(event_study_agg),
        )

        overall_att = self._compute_overall_att(group_time_atts)
        logger.info("Overall ATT: %.2f (SE: %.2f)", overall_att["att"], overall_att["se"])

        cohort_dynamics = self._compute_cohort_dynamics(group_time_atts)

        return {
            "cs_group_time_atts": group_time_atts,
            "cs_event_study": event_study_agg,
            "cs_overall_att": overall_att,
            "cs_cohort_dynamics": cohort_dynamics,
            "cs_cohort_info": cohort_info,
            "cs_comparison_group": self.comparison_group,
            "cs_with_controls": True,
            "cs_include_covariates": self.include_covariates,
            "cs_include_tract_trends": self.include_tract_trends,
        }

    def _residualize_outcome(
        self, df: pd.DataFrame, context: dict[str, Any]
    ) -> pd.DataFrame:
        """Residualize rental_price on covariates and/or tract trends."""
        logger.info("Residualizing outcome on controls...")

        # Build control matrix
        X_components = []

        # Time-invariant covariates
        if self.include_covariates:
            covariate_list = self.covariates or [
                "median_income", "median_house_value", "baseline_rent",
                "pct_bachelor", "pct_rented", "median_age", "total_population"
            ]

            covariate_data = pd.DataFrame()
            for cov in covariate_list:
                if cov in df.columns and df[cov].notna().sum() > 0:
                    # Standardize
                    cov_std = df[cov].std()
                    if cov_std > 0:
                        covariate_data[cov] = (df[cov] - df[cov].mean()) / cov_std
                        logger.info("  Added covariate: %s", cov)

            if not covariate_data.empty:
                X_components.append(covariate_data)

        # Tract-specific linear time trends
        if self.include_tract_trends:
            logger.info("  Adding tract-specific linear time trends")

            # Create time index (months since start of panel)
            df["time_index"] = (
                (df["month"] - df["month"].min()).dt.days / 30.44
            ).astype(int)

            # Interaction: tract × time
            # Use dummy variables for tracts
            tract_dummies = pd.get_dummies(
                df["tract_geoid"], prefix="tract", drop_first=True
            )

            # Multiply each tract dummy by time_index
            tract_trends = tract_dummies.multiply(df["time_index"], axis=0)
            tract_trends.columns = [col + "_trend" for col in tract_trends.columns]

            X_components.append(tract_trends)

        if not X_components:
            logger.warning("No controls to residualize on")
            return df

        # Build design matrix
        y = df["rental_price"].values
        X = pd.concat(X_components, axis=1)
        X = sm.add_constant(X, has_constant="add")

        # Fit regression
        try:
            model = sm.OLS(y, X).fit()
            residuals = model.resid

            # Replace rental_price with residuals (re-centered at original mean)
            df["rental_price_original"] = df["rental_price"]
            df["rental_price"] = residuals + df["rental_price"].mean()

            logger.info(
                "Residualized outcome: R² = %.4f, %d controls used",
                model.rsquared, X.shape[1] - 1  # -1 for constant
            )
        except Exception as e:
            logger.warning("Residualization failed: %s. Using original outcome.", e)

        return df

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
            ]["tract_geoid"].values

            logger.debug("Processing cohort %s with %d tracts", str(cohort_date)[:10], len(cohort_tracts))

            base_period = cohort_date - pd.DateOffset(months=1)

            for t in time_periods:
                if t == base_period:
                    continue

                if self.comparison_group == "nevertreated":
                    comparison_tracts = never_treated
                elif self.comparison_group == "notyettreated":
                    not_yet_treated = cohorts_df[
                        cohorts_df["first_treatment_month"] > t
                    ]["tract_geoid"].values
                    comparison_tracts = list(set(never_treated) | set(not_yet_treated))
                else:
                    raise ValueError(f"Unknown comparison_group: {self.comparison_group}")

                if len(comparison_tracts) == 0:
                    logger.warning("No comparison units for cohort %s at time %s", cohort_date, t)
                    continue

                att_result = self._estimate_single_att(
                    df=df,
                    cohort_tracts=cohort_tracts,
                    comparison_tracts=comparison_tracts,
                    cohort_date=cohort_date,
                    current_date=t,
                )

                if att_result is not None:
                    months_diff = (
                        (t.year - cohort_date.year) * 12 +
                        (t.month - cohort_date.month)
                    )

                    results.append({
                        "cohort": cohort_date,
                        "time": t,
                        "rel_time": months_diff,
                        "att": att_result["att"],
                        "se": att_result["se"],
                        "n_treated": len(cohort_tracts),
                        "n_control": len(comparison_tracts),
                    })

        return pd.DataFrame(results)

    def _estimate_single_att(
        self,
        df: pd.DataFrame,
        cohort_tracts: np.ndarray,
        comparison_tracts: list,
        cohort_date: pd.Timestamp,
        current_date: pd.Timestamp,
    ) -> dict[str, float] | None:
        """Estimate a single ATT(g,t) using outcome regression DiD."""
        pre_period = cohort_date - pd.DateOffset(months=1)

        treated_current = df[
            (df["tract_geoid"].isin(cohort_tracts)) & (df["month"] == current_date)
        ]["rental_price"]
        treated_pre = df[
            (df["tract_geoid"].isin(cohort_tracts)) & (df["month"] == pre_period)
        ]["rental_price"]

        control_current = df[
            (df["tract_geoid"].isin(comparison_tracts)) & (df["month"] == current_date)
        ]["rental_price"]
        control_pre = df[
            (df["tract_geoid"].isin(comparison_tracts)) & (df["month"] == pre_period)
        ]["rental_price"]

        if len(treated_current) == 0 or len(treated_pre) == 0:
            return None
        if len(control_current) == 0 or len(control_pre) == 0:
            return None

        # Compute first differences
        treated_df = df[
            (df["tract_geoid"].isin(cohort_tracts)) &
            (df["month"].isin([current_date, pre_period]))
        ][["tract_geoid", "month", "rental_price"]]
        treated_diff = treated_df.pivot(
            index="tract_geoid", columns="month", values="rental_price"
        )
        if current_date not in treated_diff.columns or pre_period not in treated_diff.columns:
            return None
        treated_diff["change"] = treated_diff[current_date] - treated_diff[pre_period]

        control_df = df[
            (df["tract_geoid"].isin(comparison_tracts)) &
            (df["month"].isin([current_date, pre_period]))
        ][["tract_geoid", "month", "rental_price"]]
        control_diff = control_df.pivot(
            index="tract_geoid", columns="month", values="rental_price"
        )
        if current_date not in control_diff.columns or pre_period not in control_diff.columns:
            return None
        control_diff["change"] = control_diff[current_date] - control_diff[pre_period]

        # ATT is the difference in changes
        att = treated_diff["change"].mean() - control_diff["change"].mean()

        # Standard error
        treated_var = treated_diff["change"].var()
        control_var = control_diff["change"].var()
        n_treated = len(treated_diff)
        n_control = len(control_diff)

        se = np.sqrt(treated_var / n_treated + control_var / n_control)

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

            weights = atts_at_e["n_treated"].values
            weights = weights / weights.sum()

            agg_att = np.sum(atts_at_e["att"].values * weights)
            agg_se = np.sqrt(np.sum((atts_at_e["se"].values ** 2) * (weights ** 2)))

            ci_low = agg_att - 1.96 * agg_se
            ci_high = agg_att + 1.96 * agg_se

            results.append({
                "rel_time": e,
                "att": agg_att,
                "se": agg_se,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "n_cohorts": len(atts_at_e),
            })

        event_study_df = pd.DataFrame(results).sort_values("rel_time")

        return event_study_df

    def _compute_overall_att(self, group_time_atts: pd.DataFrame) -> dict[str, float]:
        """Compute overall post-treatment ATT."""
        if group_time_atts.empty:
            return {"att": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan}

        post_treatment = group_time_atts[group_time_atts["rel_time"] >= 0].copy()

        if post_treatment.empty:
            return {"att": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan}

        weights = post_treatment["n_treated"].values
        weights = weights / weights.sum()

        overall_att = np.sum(post_treatment["att"].values * weights)
        overall_se = np.sqrt(np.sum((post_treatment["se"].values ** 2) * (weights ** 2)))

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
                cohort_dynamics.append({
                    "cohort": cohort,
                    "rel_time": row["rel_time"],
                    "att": row["att"],
                    "se": row["se"],
                    "ci_low": row["att"] - 1.96 * row["se"],
                    "ci_high": row["att"] + 1.96 * row["se"],
                })

        return pd.DataFrame(cohort_dynamics)
