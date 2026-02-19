"""Event study analyzer for Difference-in-Differences.

Estimates dynamic treatment effects via relative-time dummies with
tract and time fixed effects, and clustered standard errors at tract level.

⚠️ **WARNING: Staggered Treatment Timing**

This implements a standard Two-Way Fixed Effects (TWFE) event study. In settings
with staggered treatment adoption and heterogeneous treatment effects, TWFE can
produce BIASED estimates due to "negative weighting" problems where already-treated
units serve as implicit controls (Goodman-Bacon 2021, Sun & Abraham 2020).

**For staggered DiD with potential heterogeneous effects, use:**
`CallawaySantAnnaAnalyzer` (robust alternative, see callaway_santanna.py)

**When TWFE is appropriate:**
- All units treated at the same time (no staggering)
- Treatment effects are homogeneous across units and time
- As a robustness check alongside Callaway-Sant'Anna

**Equation estimated**

    Y_{it} = α + ∑_{k≠-1} β_k · 1[rel_time_{it} = k] + γ_i + δ_t + ε_{it}

**Variable definitions**

- **Y_{it}** (outcome): `rental_price` — average rental price (ZORI-based, area-weighted)
  in census tract i in month t (dollars).

- **rel_time_{it}** (relative event time): `months_since_treatment` — number of months
  from month t to the tract’s first STR prohibition date. For never-treated tracts
  it is set to the reference value -1 (so they contribute only to fixed effects).
  Binned as: ≤-13 (far lead), -12,…, -2, -1 (reference), 0,…, 36, ≥37 (far lag).

- **1[rel_time_{it} = k]** (event dummies): indicator that tract i in month t is at
  relative time k. The period k = -1 (one month before treatment) is the reference
  category (omitted), so β_{-1} = 0 by construction.

- **γ_i** (tract fixed effects): tract dummies (one category omitted). Control for
  time-invariant tract characteristics (e.g. location, baseline amenities).

- **δ_t** (time fixed effects): month dummies (one category omitted). Control for
  common time trends (e.g. city-wide rent growth, seasonality).

- **ε_{it}**: error term. Standard errors are clustered at the tract (i) level.

**Treatment definition**

- **Treatment**: An STR (short-term rental) prohibition is in effect in tract i
  in month t. This is determined from the House Share Prohibited Buildings list:
  for each tract, `first_prohibition_date` is the earliest prohibition date among
  buildings in that tract (from a spatial join). Then:
  - `treated_{it} = 1` if month t ≥ first_prohibition_date in tract i,
  - `months_since_treatment_{it} = (year_t - year_0)*12 + (month_t - month_0)`
    where (year_0, month_0) is the tract’s first_prohibition_date.
- **Never-treated tracts**: tracts with no buildings in the prohibition list;
  for these, `months_since_treatment` is missing and set to -1 (reference) so
  they act as controls.

**Interpretation**

- **β_k** (k ≠ -1): average causal effect on rental price in tract-month (i,t)
  that is k months after (k>0) or before (k<0) the tract’s first prohibition,
  relative to k = -1 (one month before treatment), holding tract and time FEs
  fixed. Effects are in dollars per month (same units as Y_{it}).
- **Parallel trends**: pre-treatment coefficients β_k for k ≤ -2 should be
  close to zero if the parallel trends assumption holds.
"""

import logging
from typing import Any

import pandas as pd
import statsmodels.api as sm
from statsmodels.tools.tools import add_constant

from pipeline.base import Analyzer

logger = logging.getLogger(__name__)

# Relative time window: event times from -LEAD_LIMIT to +LAG_LIMIT
LEAD_LIMIT = 12   # 1 year of pre-treatment periods (matches data availability for largest cohorts)
LAG_LIMIT = 36    # 3 years of post-treatment periods
# Bins for far leads/lags to avoid too many dummies
LEAD_BIN_LABEL = -999  # <= -LEAD_LIMIT - 1
LAG_BIN_LABEL = 999   # >= LAG_LIMIT + 1
REFERENCE_PERIOD = -1


class EventStudyAnalyzer(Analyzer):
    """Estimate event study regression for DiD: relative-time dummies + tract FE + time FE."""

    def __init__(self, include_covariates: bool = False, covariates: list[str] | None = None) -> None:
        """Initialize the event study analyzer.

        Args:
            include_covariates: If True, will attempt to include tract-level covariates.
            covariates: List of covariate column names to include. If None, uses defaults.
        """
        super().__init__(
            "event_study_analysis",
            "Event study regression with two-way fixed effects and clustered SEs",
        )
        self.include_covariates = include_covariates
        self.covariates = covariates

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run event study regression and return coefficients and CIs for plotting."""
        logger.info("Starting event study analysis...")

        did_panel = context.get("did_panel")
        if did_panel is None:
            logger.error("did_panel not found in context")
            raise ValueError("did_panel not found in context")

        df = did_panel.copy()
        df = df.dropna(subset=["rental_price"]).reset_index(drop=True)
        if df.empty:
            logger.error("No non-missing rental_price in did_panel")
            raise ValueError("No valid observations for event study")

        # Panel structure and balance checks
        n_tracts = df["tract_geoid"].nunique()
        n_months = df["month"].nunique()
        obs_per_tract = df.groupby("tract_geoid").size()
        n_obs = len(df)
        is_balanced = obs_per_tract.nunique() == 1 and obs_per_tract.iloc[0] == n_months
        month_min, month_max = df["month"].min(), df["month"].max()
        logger.info(
            "Panel structure: %d tracts, %d months, %d obs; date range %s to %s",
            n_tracts,
            n_months,
            n_obs,
            str(month_min)[:10],
            str(month_max)[:10],
        )
        logger.info(
            "Panel balance: obs per tract min=%d, max=%d, mean=%.1f; balanced=%s",
            obs_per_tract.min(),
            obs_per_tract.max(),
            obs_per_tract.mean(),
            is_balanced,
        )
        # Relative time range in raw data (among treated obs)
        rel_raw = df["months_since_treatment"].dropna()
        if len(rel_raw) > 0:
            rel_min, rel_max = int(rel_raw.min()), int(rel_raw.max())
            logger.info(
                "Relative event time in data: min=%d, max=%d months (binned to ±%d for estimation)",
                rel_min,
                rel_max,
                LEAD_LIMIT,
            )

        # Build relative-time bin (reference = -1; never-treated coded as reference)
        df["rel_time_raw"] = df["months_since_treatment"].copy()
        # Never-treated: no event time -> reference period
        df.loc[df["rel_time_raw"].isna(), "rel_time_raw"] = REFERENCE_PERIOD
        # Bin far leads/lags
        df["rel_time_bin"] = df["rel_time_raw"].astype(float)
        df.loc[df["rel_time_bin"] < -LEAD_LIMIT, "rel_time_bin"] = float(LEAD_BIN_LABEL)
        df.loc[df["rel_time_bin"] > LAG_LIMIT, "rel_time_bin"] = float(LAG_BIN_LABEL)
        df["rel_time_bin"] = df["rel_time_bin"].astype(int)

        # Build design matrix: rel_time dummies (omit -1) + tract + month
        # We use patsy-style via pd.get_dummies with drop_first=False, then drop reference
        rel_bins = sorted(df["rel_time_bin"].unique())
        ref_bin = REFERENCE_PERIOD
        if ref_bin not in rel_bins:
            ref_bin = int(df["rel_time_bin"].mode().iloc[0])
        rel_dummies = pd.get_dummies(df["rel_time_bin"], prefix="rel", dtype=float)
        if f"rel_{ref_bin}" in rel_dummies.columns:
            rel_dummies = rel_dummies.drop(columns=[f"rel_{ref_bin}"])

        # Tract and month as categorical (drop first to avoid collinearity)
        tract_dummies = pd.get_dummies(df["tract_geoid"], prefix="tract", drop_first=True, dtype=float)
        month_rank = df["month"].astype("datetime64[ns]").rank(method="dense").astype(int)
        month_dummies = pd.get_dummies(month_rank, prefix="month", drop_first=True, dtype=float)

        # Add covariates if requested
        X_components = [rel_dummies, tract_dummies, month_dummies]
        covariates_used = []

        if self.include_covariates:
            covariate_data = pd.DataFrame()

            # Define potential covariates
            potential_covariates = self.covariates or [
                "median_income", "median_house_value", "baseline_rent",
                "pct_bachelor", "pct_rented", "median_age", "total_population"
            ]

            for cov in potential_covariates:
                if cov in df.columns:
                    # Check if covariate has variation
                    if df[cov].notna().sum() > 0 and df[cov].nunique() > 1:
                        # Standardize covariate (mean=0, sd=1)
                        cov_std = df[cov].std()
                        if cov_std > 0:
                            covariate_data[cov] = (df[cov] - df[cov].mean()) / cov_std
                            covariates_used.append(cov)
                            logger.info("Added covariate: %s", cov)

            if not covariate_data.empty:
                X_components.append(covariate_data)
                logger.info("Including %d covariates in regression: %s",
                           len(covariates_used), ", ".join(covariates_used))
            else:
                logger.warning("No valid covariates found")

        y = df["rental_price"].values
        X = pd.concat(X_components, axis=1)
        X = add_constant(X, has_constant="add")

        # Drop any column that is constant (can happen with few clusters)
        const_cols = X.columns[X.nunique() <= 1]
        if len(const_cols) > 0:
            X = X.drop(columns=list(const_cols))
            logger.info("Dropped %d constant columns from design matrix", len(const_cols))

        try:
            model = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": df["tract_geoid"]})
        except Exception as e:
            logger.warning("Clustered OLS failed (%s), falling back to HC1 robust SE", e)
            model = sm.OLS(y, X).fit(cov_type="HC1")

        # Extract event study coefficients: only "rel_*" params
        rel_params = [c for c in model.params.index if c.startswith("rel_")]
        event_results = []
        for p in rel_params:
            # Parse period from name "rel_-5" -> -5, "rel_999" -> 999
            period_str = p.replace("rel_", "")
            try:
                period = int(period_str)
            except ValueError:
                period = 0
            coef = model.params[p]
            se = model.bse[p]
            ci_lo = model.conf_int().loc[p, 0]
            ci_hi = model.conf_int().loc[p, 1]
            event_results.append({
                "rel_time": period,
                "coef": coef,
                "se": se,
                "ci_low": ci_lo,
                "ci_high": ci_hi,
            })

        event_df = pd.DataFrame(event_results).sort_values("rel_time")
        # Add reference period as (ref, 0, 0, 0, 0)
        ref_row = pd.DataFrame([{
            "rel_time": REFERENCE_PERIOD,
            "coef": 0.0,
            "se": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
        }])
        event_df = pd.concat([ref_row, event_df], ignore_index=True).sort_values("rel_time").reset_index(drop=True)

        logger.info(
            "Event study: %d relative-time coefficients (ref = %d); N = %d",
            len(event_df) - 1,
            REFERENCE_PERIOD,
            len(df),
        )
        if hasattr(model, "rsquared"):
            logger.info("Event study R-squared: %.4f", model.rsquared)

        result = {
            "event_study_results": event_df,
            "event_study_model": model,
            "event_study_n_obs": len(df),
            "event_study_rel_time_range": (LEAD_LIMIT, LAG_LIMIT),  # (-12, 36) for plot x-axis
            "event_study_panel_summary": {
                "n_tracts": n_tracts,
                "n_months": n_months,
                "n_obs": n_obs,
                "obs_per_tract_min": int(obs_per_tract.min()),
                "obs_per_tract_max": int(obs_per_tract.max()),
                "obs_per_tract_mean": float(obs_per_tract.mean()),
                "is_balanced": is_balanced,
                "month_min": month_min,
                "month_max": month_max,
            },
        }

        if self.include_covariates:
            result["event_study_covariates_used"] = covariates_used
            result["event_study_with_covariates"] = True

        return result
