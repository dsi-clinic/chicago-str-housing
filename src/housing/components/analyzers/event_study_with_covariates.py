"""Event study analyzer with covariate controls for Difference-in-Differences.

Extends the baseline event study by including tract-level covariates
to control for confounding from selection into treatment based on
observable characteristics.

**Equation estimated**

    Y_{it} = α + ∑_{k≠-1} β_k · 1[rel_time_{it} = k] + γ·X_i + γ_i + δ_t + ε_{it}

**Additional terms compared to baseline event study**

- **X_i** (tract covariates): Time-invariant tract characteristics that may
  confound the relationship between STR prohibition and rental prices.
  Includes: median_income, median_house_value, baseline_rent, pct_bachelor, etc.

- **γ** (covariate coefficients): Effect of each covariate on rental price.

**Why include covariates?**

Even with tract and time fixed effects, pre-treatment trends may diverge
if treated and control tracts differ on time-invariant characteristics that
interact with time trends. Including baseline covariates can:

1. Absorb variation that would otherwise bias treatment effect estimates
2. Improve precision by reducing residual variance
3. Provide robustness check: if treatment effects are similar with/without
   covariates, the parallel trends assumption is more plausible
"""

import logging
import warnings
from typing import Any

import numpy as np
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


class EventStudyWithCovariatesAnalyzer(Analyzer):
    """Estimate event study regression with covariates + two-way fixed effects."""

    def __init__(self, covariates: list[str] | None = None) -> None:
        """Initialize the event study analyzer with covariates.

        Args:
            covariates: List of covariate column names to include.
                       If None, will use all available covariates from context.
        """
        super().__init__(
            "event_study_with_covariates",
            "Event study regression with covariates, tract FE, time FE, and clustered SEs",
        )
        self.covariates = covariates

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run event study regression with covariates and return coefficients and CIs."""
        logger.info("Starting event study analysis with covariates...")

        # Try to get panel with covariates first, fall back to regular panel
        did_panel = context.get("did_panel_with_covariates")
        if did_panel is None:
            logger.warning(
                "did_panel_with_covariates not found, using did_panel without covariates"
            )
            did_panel = context.get("did_panel")

        if did_panel is None:
            logger.error("No DID panel found in context")
            raise ValueError("No DID panel found in context")

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

        # Build design matrix: rel_time dummies (omit -1) + covariates + tract + month
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

        # Add covariates if available
        covariate_data = pd.DataFrame()
        covariates_used = []

        if self.covariates is not None:
            # Use specified covariates
            potential_covariates = self.covariates
        else:
            # Auto-detect from context
            potential_covariates = context.get("covariate_columns", [])
            if not potential_covariates:
                # Default list
                potential_covariates = [
                    "median_income", "median_house_value", "baseline_rent",
                    "pct_bachelor", "pct_rented", "median_age", "total_population"
                ]

        for cov in potential_covariates:
            if cov in df.columns:
                # Use only finite values for checks and standardization
                ser = df[cov].replace([np.inf, -np.inf], np.nan)
                n_ok = ser.notna().sum()
                n_unique = ser.nunique()
                if n_ok > 0 and n_unique > 1:
                    mean_val = ser.mean()
                    std_val = ser.std()
                    if not np.isfinite(std_val) or std_val == 0:
                        continue
                    covariate_data[cov] = (ser - mean_val) / std_val
                    covariates_used.append(cov)
                    logger.info("Added covariate: %s (mean=%.2f, sd=%.2f)",
                               cov, mean_val, std_val)

        if covariates_used:
            logger.info("Including %d covariates in regression: %s",
                       len(covariates_used), ", ".join(covariates_used))
        else:
            logger.warning("No valid covariates found, running without covariates")

        # Construct full design matrix
        y = df["rental_price"].values
        X_components = [rel_dummies, tract_dummies, month_dummies]
        if not covariate_data.empty:
            X_components.append(covariate_data)

        X = pd.concat(X_components, axis=1)
        X = add_constant(X, has_constant="add")

        # Drop any column that is constant (can happen with few clusters)
        const_cols = X.columns[X.nunique() <= 1]
        if len(const_cols) > 0:
            X = X.drop(columns=list(const_cols))
            logger.info("Dropped %d constant columns from design matrix", len(const_cols))

        # Drop rows with any inf/nan in X or y so OLS does not fail
        valid = np.isfinite(X).all(axis=1) & np.isfinite(y)
        if not valid.all():
            n_drop = (~valid).sum()
            logger.warning(
                "Dropping %d rows with non-finite values in design or outcome (keeping %d)",
                n_drop, valid.sum(),
            )
            X = X.loc[valid].reset_index(drop=True)
            y = y[valid]
            groups = df.loc[valid, "tract_geoid"].values
        else:
            groups = df["tract_geoid"].values

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="invalid value encountered in sqrt",
                category=RuntimeWarning,
            )
            try:
                model = sm.OLS(y, X).fit(
                    cov_type="cluster", cov_kwds={"groups": groups}
                )
                if not np.isfinite(model.bse).all():
                    logger.warning(
                        "Clustered SE produced non-finite values, falling back to HC1 robust SE"
                    )
                    model = sm.OLS(y, X).fit(cov_type="HC1")
            except Exception as e:
                logger.warning(
                    "Clustered OLS failed (%s), falling back to HC1 robust SE", e
                )
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

        # Extract covariate coefficients for reporting
        covariate_results = []
        for cov in covariates_used:
            if cov in model.params.index:
                coef = model.params[cov]
                se = model.bse[cov]
                ci_lo = model.conf_int().loc[cov, 0]
                ci_hi = model.conf_int().loc[cov, 1]
                covariate_results.append({
                    "covariate": cov,
                    "coef": coef,
                    "se": se,
                    "ci_low": ci_lo,
                    "ci_high": ci_hi,
                    "significant": abs(coef / se) > 1.96 if se > 0 else False
                })

        covariate_df = pd.DataFrame(covariate_results)

        n_used = len(y)
        logger.info(
            "Event study (with covariates): %d relative-time coefficients (ref = %d); N = %d",
            len(event_df) - 1,
            REFERENCE_PERIOD,
            n_used,
        )
        if hasattr(model, "rsquared"):
            logger.info("Event study R-squared: %.4f", model.rsquared)

        if not covariate_df.empty:
            logger.info("Covariate coefficients:")
            for _, row in covariate_df.iterrows():
                sig_marker = "***" if row["significant"] else ""
                logger.info("  %s: %.2f (SE=%.2f) %s",
                           row["covariate"], row["coef"], row["se"], sig_marker)

        return {
            "event_study_results_with_covariates": event_df,
            "event_study_covariate_effects": covariate_df,
            "event_study_model_with_covariates": model,
            "event_study_n_obs": n_used,
            "event_study_covariates_used": covariates_used,
            "event_study_rel_time_range": (LEAD_LIMIT, LAG_LIMIT),
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
