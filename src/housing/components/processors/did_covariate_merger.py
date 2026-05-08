"""Merge census and tract covariates into DID panel data.

This processor enriches the DID panel with tract-level characteristics
(median income, house value, demographics) to control for confounding
in the event study analysis.
"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class DIDCovariateProcessor(DataProcessor):
    """Add tract-level covariates to DID panel for confounding control.

    Merges time-invariant tract characteristics (census demographics,
    baseline rental prices) into the panel data to enable covariate
    adjustment in the event study regression.
    """

    def __init__(self) -> None:
        """Initialize the processor."""
        super().__init__(
            "did_panel_with_covariates",
            "Merge census and tract covariates into DID panel",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the processing."""
        logger.info("Merging covariates into DID panel...")

        # Get DID panel
        did_panel = context.get("did_panel")
        if did_panel is None:
            raise ValueError("did_panel not found in context")

        # Make a copy to avoid modifying original
        panel_with_covariates = did_panel.copy()

        # 1. Merge census data if available
        census_data = context.get("census_data")
        if census_data is not None:
            panel_with_covariates = self._merge_census_data(
                panel_with_covariates, census_data
            )
        else:
            logger.warning(
                "census_data not found in context, skipping census covariates"
            )

        # 2. Calculate baseline rental price for each tract (pre-treatment average)
        panel_with_covariates = self._add_baseline_rent(panel_with_covariates)

        # 3. Add ever_treated indicator if not already present
        if "ever_treated" not in panel_with_covariates.columns:
            panel_with_covariates = self._add_ever_treated(panel_with_covariates)

        # 4. Log covariate summary
        self._log_covariate_summary(panel_with_covariates)

        return {
            "did_panel_with_covariates": panel_with_covariates,
            "covariate_columns": self._get_covariate_columns(panel_with_covariates),
        }

    def _merge_census_data(
        self, panel: pd.DataFrame, census: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge census covariates into panel data."""
        # Standardize tract identifiers for merging
        # Panel uses 'tract_geoid', census uses 'tract_id'

        census_cols = [
            "tract_id",
            "median_income",
            "median_house_value",
            "median_age",
            "pct_bachelor",
            "pct_rented",
            "total_population",
        ]

        # Keep only available columns
        available_cols = [col for col in census_cols if col in census.columns]
        census_subset = census[available_cols].copy()
        census_subset["tract_id"] = census_subset["tract_id"].astype(str)

        panel = panel.copy()
        panel["tract_geoid"] = panel["tract_geoid"].astype(str)

        # Merge (many-to-one: many panel rows to one census row per tract)
        merged = panel.merge(
            census_subset, left_on="tract_geoid", right_on="tract_id", how="left"
        )

        # Drop redundant tract_id column if it exists
        if "tract_id" in merged.columns:
            merged = merged.drop(columns=["tract_id"])

        n_total = len(merged)
        n_matched = (
            merged["median_income"].notna().sum()
            if "median_income" in merged.columns
            else 0
        )
        pct_matched = (n_matched / n_total * 100) if n_total > 0 else 0

        logger.info(
            "Merged census data: %d/%d observations matched (%.1f%%)",
            n_matched,
            n_total,
            pct_matched,
        )

        return merged

    def _add_baseline_rent(self, panel: pd.DataFrame) -> pd.DataFrame:
        """Calculate baseline (pre-treatment) rental price for each tract."""
        # Define pre-treatment period as before first treatment month
        first_treatment = panel.loc[panel["treated"] == 1, "month"].min()

        if pd.isna(first_treatment):
            logger.warning(
                "No treated observations found, cannot calculate baseline rent"
            )
            panel["baseline_rent"] = panel["rental_price"]
            return panel

        # Calculate mean rent in pre-treatment period for each tract
        pre_period = panel[panel["month"] < first_treatment].copy()

        baseline = (
            pre_period.groupby("tract_geoid")["rental_price"]
            .mean()
            .reset_index()
            .rename(columns={"rental_price": "baseline_rent"})
        )

        # Merge back into panel
        panel = panel.merge(baseline, on="tract_geoid", how="left")

        # For tracts without pre-treatment data, use their first observed rent
        if panel["baseline_rent"].isna().any():
            first_obs_rent = (
                panel.groupby("tract_geoid")["rental_price"]
                .first()
                .reset_index()
                .rename(columns={"rental_price": "first_rent"})
            )
            panel = panel.merge(first_obs_rent, on="tract_geoid", how="left")
            panel["baseline_rent"] = panel["baseline_rent"].fillna(panel["first_rent"])
            panel = panel.drop(columns=["first_rent"])

        logger.info(
            "Added baseline_rent covariate for %d tracts",
            panel["tract_geoid"].nunique(),
        )

        return panel

    def _add_ever_treated(self, panel: pd.DataFrame) -> pd.DataFrame:
        """Add ever_treated indicator (1 if tract ever gets treated)."""
        ever_treated = panel.groupby("tract_geoid")["treated"].max()
        panel["ever_treated"] = panel["tract_geoid"].map(ever_treated)

        n_ever_treated = (panel["ever_treated"] == 1).sum()
        n_never_treated = (panel["ever_treated"] == 0).sum()

        logger.info(
            "Treatment groups: %d ever-treated obs, %d never-treated obs",
            n_ever_treated,
            n_never_treated,
        )

        return panel

    def _get_covariate_columns(self, panel: pd.DataFrame) -> list[str]:
        """Return list of covariate column names available in panel."""
        potential_covariates = [
            "median_income",
            "median_house_value",
            "median_age",
            "pct_bachelor",
            "pct_rented",
            "total_population",
            "baseline_rent",
        ]

        return [col for col in potential_covariates if col in panel.columns]

    def _log_covariate_summary(self, panel: pd.DataFrame) -> None:
        """Log summary statistics of covariates by treatment group."""
        if "ever_treated" not in panel.columns:
            return

        # Get one observation per tract for summary
        tract_data = panel.drop_duplicates(subset="tract_geoid")

        covariates = self._get_covariate_columns(panel)

        if not covariates:
            logger.warning("No covariates found in panel")
            return

        logger.info("Covariate Summary by Treatment Group:")

        for cov in covariates:
            treated_mean = tract_data.loc[tract_data["ever_treated"] == 1, cov].mean()
            control_mean = tract_data.loc[tract_data["ever_treated"] == 0, cov].mean()

            diff = treated_mean - control_mean
            pct_diff = (diff / control_mean * 100) if control_mean != 0 else 0

            logger.info(
                "  %s: Treated=%.2f, Control=%.2f, Diff=%.2f (%.1f%%)",
                cov,
                treated_mean,
                control_mean,
                diff,
                pct_diff,
            )
