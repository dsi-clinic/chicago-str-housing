"""Callaway & Sant'Anna (2021) estimator for staggered DiD.

Implements the group-time average treatment effect estimator that is robust
to heterogeneous treatment effects in staggered adoption designs.

**Key advantages over TWFE:**

1. **No negative weights**: Only compares treated units to not-yet-treated
   or never-treated units (never uses already-treated as controls)

2. **Heterogeneity-robust**: Allows treatment effects to vary by:
   - Treatment cohort (when first treated)
   - Time since treatment (dynamic effects)
   - Calendar time (time-varying effects)

3. **Transparent aggregation**: Estimates group-time ATTs first, then
   aggregates to event study or overall ATT with known weights

**Methodology:**

For each cohort g (defined by first treatment date) and time period t:
  ATT(g,t) = E[Y_t - Y_{g-1} | G_g=1] - E[Y_t - Y_{g-1} | C=1]

where:
  - G_g = 1 if unit was first treated in period g
  - C = 1 if unit is in the comparison group (never/not-yet-treated)
  - Y_{g-1} is the outcome in the period before treatment

**Aggregation to event study:**

For each relative time e (e.g., e=0 is treatment period, e=-1 is one period before):
  ATT(e) = weighted average of ATT(g, g+e) across cohorts g

**Reference:**
Callaway, Brantly, and Pedro HC Sant'Anna. "Difference-in-differences with
multiple time periods." Journal of Econometrics 225.2 (2021): 200-230.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

# Constants
MAX_PRE_TIME = 12   # Maximum pre-treatment periods (1 year, matches data for largest cohorts)
MAX_POST_TIME = 36  # Maximum post-treatment periods (3 years)


class CallawaySantAnnaAnalyzer(Analyzer):
    """Estimate Callaway & Sant'Anna (2021) group-time ATTs for staggered DiD."""

    def __init__(
        self,
        comparison_group: str = "nevertreated",
        anticipation: int = 0,
        min_cohort_size: int = 10,
    ) -> None:
        """Initialize the Callaway & Sant'Anna analyzer.

        Args:
            comparison_group: Which units to use as controls:
                - "nevertreated": Only never-treated units (preferred)
                - "notyettreated": Not-yet-treated units (allows more comparisons)
            anticipation: Number of periods before treatment that may have anticipation effects.
                         If anticipation=1, we assume treatment effects may begin 1 period early.
            min_cohort_size: Minimum number of units in a cohort to estimate ATT.
        """
        super().__init__(
            "callaway_santanna_analysis",
            "Callaway & Sant'Anna (2021) group-time ATT estimator",
        )
        self.comparison_group = comparison_group
        self.anticipation = anticipation
        self.min_cohort_size = min_cohort_size

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Estimate group-time ATTs and aggregate to event study."""
        logger.info("Starting Callaway & Sant'Anna analysis...")
        logger.info("Comparison group: %s", self.comparison_group)

        did_panel = context.get("did_panel")
        if did_panel is None:
            logger.error("did_panel not found in context")
            raise ValueError("did_panel not found in context")

        df = did_panel.copy()
        df = df.dropna(subset=["rental_price"]).reset_index(drop=True)

        # Step 1: Identify treatment cohorts
        cohort_info = self._identify_cohorts(df)
        logger.info(
            "Identified %d treatment cohorts and %d never-treated tracts",
            len(cohort_info["treated_cohorts"]),
            cohort_info["n_never_treated"],
        )

        # Step 2: Estimate group-time ATTs
        group_time_atts = self._estimate_group_time_atts(df, cohort_info)
        logger.info("Estimated %d group-time ATTs", len(group_time_atts))

        # Step 3: Aggregate to event study
        event_study_agg = self._aggregate_to_event_study(group_time_atts, df)
        logger.info(
            "Aggregated to event study with %d relative time periods",
            len(event_study_agg),
        )

        # Step 4: Compute overall ATT (post-treatment average)
        overall_att = self._compute_overall_att(group_time_atts)
        logger.info("Overall ATT: %.2f (SE: %.2f)", overall_att["att"], overall_att["se"])

        # Step 5: Compute cohort-specific dynamic effects
        cohort_dynamics = self._compute_cohort_dynamics(group_time_atts)

        return {
            "cs_group_time_atts": group_time_atts,
            "cs_event_study": event_study_agg,
            "cs_overall_att": overall_att,
            "cs_cohort_dynamics": cohort_dynamics,
            "cs_cohort_info": cohort_info,
            "cs_comparison_group": self.comparison_group,
        }

    def _identify_cohorts(self, df: pd.DataFrame) -> dict[str, Any]:
        """Identify treatment cohorts and never-treated units."""
        # Get first treatment date for each tract
        tract_first_treatment = (
            df[df["treated"] == 1]
            .groupby("tract_geoid")["month"]
            .min()
            .reset_index()
            .rename(columns={"month": "first_treatment_month"})
        )

        # Identify never-treated tracts
        treated_tracts = tract_first_treatment["tract_geoid"].unique()
        all_tracts = df["tract_geoid"].unique()
        never_treated_tracts = set(all_tracts) - set(treated_tracts)

        # Get cohort sizes
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

        # Get unique cohorts and time periods
        cohorts = sorted(cohorts_df["first_treatment_month"].unique())
        time_periods = sorted(df["month"].unique())

        for cohort_date in cohorts:
            # Get tracts in this cohort
            cohort_tracts = cohorts_df[
                cohorts_df["first_treatment_month"] == cohort_date
            ]["tract_geoid"].values

            logger.debug("Processing cohort %s with %d tracts", str(cohort_date)[:10], len(cohort_tracts))

            # Base period is one month before treatment
            base_period = cohort_date - pd.DateOffset(months=1)

            for t in time_periods:
                # Skip the base period itself (ATT is trivially 0)
                if t == base_period:
                    continue

                # Define comparison group
                if self.comparison_group == "nevertreated":
                    comparison_tracts = never_treated
                elif self.comparison_group == "notyettreated":
                    # Not-yet-treated: never-treated + those treated after t
                    not_yet_treated = cohorts_df[
                        cohorts_df["first_treatment_month"] > t
                    ]["tract_geoid"].values
                    comparison_tracts = list(set(never_treated) | set(not_yet_treated))
                else:
                    raise ValueError(f"Unknown comparison_group: {self.comparison_group}")

                if len(comparison_tracts) == 0:
                    logger.warning("No comparison units for cohort %s at time %s", cohort_date, t)
                    continue

                # Estimate ATT(g,t) using difference-in-differences
                att_result = self._estimate_single_att(
                    df=df,
                    cohort_tracts=cohort_tracts,
                    comparison_tracts=comparison_tracts,
                    cohort_date=cohort_date,
                    current_date=t,
                )

                if att_result is not None:
                    # Calculate relative time
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
        """Estimate a single ATT(g,t) using difference-in-differences.

        ATT(g,t) = E[Y_t - Y_{g-1} | G=1] - E[Y_t - Y_{g-1} | C=1]
        """
        pre_period = cohort_date - pd.DateOffset(months=1)

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

        if len(treated_diff) == 0 or len(control_diff) == 0:
            return None

        att = treated_diff["change"].mean() - control_diff["change"].mean()
        n_treated = len(treated_diff)
        n_control = len(control_diff)
        treated_var = treated_diff["change"].var()
        control_var = control_diff["change"].var()
        if n_control > 0 and (treated_var > 0 or control_var > 0):
            se = np.sqrt(treated_var / n_treated + control_var / n_control)
        else:
            se = np.nan
        return {"att": att, "se": se}

    def _aggregate_to_event_study(
        self, group_time_atts: pd.DataFrame, df: pd.DataFrame
    ) -> pd.DataFrame:
        """Aggregate group-time ATTs to event study by relative time.

        For each relative time e, compute weighted average of ATT(g, g+e)
        where weights are proportional to cohort size.
        """
        if group_time_atts.empty:
            return pd.DataFrame()

        # Get relative times
        rel_times = sorted(group_time_atts["rel_time"].unique())
        rel_times = [rt for rt in rel_times if -MAX_PRE_TIME <= rt <= MAX_POST_TIME]

        results = []

        for e in rel_times:
            # Get all ATT(g, g+e) for this relative time
            atts_at_e = group_time_atts[group_time_atts["rel_time"] == e].copy()

            if atts_at_e.empty:
                continue

            # Weight by cohort size (number of treated units)
            weights = atts_at_e["n_treated"].values
            weights = weights / weights.sum()

            # Weighted average of ATTs
            agg_att = np.sum(atts_at_e["att"].values * weights)

            # Aggregate standard error (conservative: assumes independence)
            agg_se = np.sqrt(np.sum((atts_at_e["se"].values ** 2) * (weights ** 2)))

            # Confidence interval
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
        """Compute overall post-treatment ATT (weighted average across all g,t)."""
        if group_time_atts.empty:
            return {"att": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan}

        # Only post-treatment periods
        post_treatment = group_time_atts[group_time_atts["rel_time"] >= 0].copy()

        if post_treatment.empty:
            return {"att": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan}

        # Weight by cohort size
        weights = post_treatment["n_treated"].values
        weights = weights / weights.sum()

        # Weighted average
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
