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


def _canonical_tract_geoid(series: pd.Series) -> pd.Series:
    """Return 11-digit GEOID strings for joining panel to census.

    Handles integer/float GEOIDs (e.g. from CSV), ``str`` with trailing ``.0``,
    and normal ``GEOID`` strings from shapefiles.
    """
    num = pd.to_numeric(series, errors="coerce")
    whole = num.notna() & (num == num.round()) & (num >= 0) & (num < 10**12)
    out = pd.Series(pd.NA, index=series.index, dtype=object)
    out.loc[whole] = (
        num.loc[whole].round(0).astype("int64").map(lambda x: f"{int(x):011d}")
    )

    remainder = series.notna() & out.isna()
    for idx in series.index[remainder]:
        raw = str(series.loc[idx]).strip()
        if raw.lower() in ("nan", "none", ""):
            continue
        if raw.endswith(".0") and raw[:-2].isdigit():
            raw = raw[:-2]
        if raw.isdigit():
            out.loc[idx] = raw.zfill(11)
        else:
            out.loc[idx] = raw
    return out


# Minimum string length to slice state (1) + county (3) from an 11-digit tract GEOID
_MIN_GEOID_STR_LEN_FOR_COUNTY_FIPS = 5

# Census columns merged from ACS; imputed with county medians when tract-level is missing
_CENSUS_COVARIATE_COLS = [
    "median_income",
    "median_house_value",
    "median_age",
    "pct_bachelor",
    "pct_rented",
    "total_population",
]


def _county_fips_from_census_row(census: pd.DataFrame) -> pd.Series:
    """3-digit county FIPS aligned to census rows."""
    if "county_fips" in census.columns:
        return (
            census["county_fips"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(3)
        )
    if "tract_id" in census.columns:
        tid = _canonical_tract_geoid(census["tract_id"])
        out = pd.Series(pd.NA, index=tid.index, dtype=object)
        ok = tid.notna() & (
            tid.astype(str).str.len() >= _MIN_GEOID_STR_LEN_FOR_COUNTY_FIPS
        )
        out.loc[ok] = tid.loc[ok].astype(str).str.slice(2, 5)
        return out
    return pd.Series(pd.NA, index=census.index)


def _county_fips_from_panel_geoid(panel_geoid: pd.Series) -> pd.Series:
    """3-digit county FIPS from tract GEOID (positions 2–4 = county within state)."""
    keys = _canonical_tract_geoid(panel_geoid)
    out = pd.Series(pd.NA, index=keys.index, dtype=object)
    ok = keys.notna() & (
        keys.astype(str).str.len() >= _MIN_GEOID_STR_LEN_FOR_COUNTY_FIPS
    )
    out.loc[ok] = keys.loc[ok].astype(str).str.slice(2, 5)
    return out


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

        panel_key = _canonical_tract_geoid(panel["tract_geoid"])
        census_key = _canonical_tract_geoid(census_subset["tract_id"])
        panel_merge = panel.copy()
        panel_merge["_census_merge_key"] = panel_key
        census_subset = census_subset.copy()
        census_subset["_census_merge_key"] = census_key
        dupes = census_subset["_census_merge_key"].duplicated(keep=False).sum()
        if dupes:
            n_before = len(census_subset)
            census_subset = census_subset.drop_duplicates(
                subset=["_census_merge_key"], keep="first"
            )
            logger.info(
                "Deduplicated census on tract key: %d -> %d rows (%d duplicate keys)",
                n_before,
                len(census_subset),
                dupes,
            )

        merged = panel_merge.merge(
            census_subset.drop(columns=["tract_id"], errors="ignore"),
            on="_census_merge_key",
            how="left",
            suffixes=("", "_census_dup"),
        )
        merged = merged.drop(columns=["_census_merge_key"], errors="ignore")
        dup_cols = [c for c in merged.columns if c.endswith("_census_dup")]
        merged = merged.drop(columns=dup_cols, errors="ignore")

        n_total = len(merged)
        n_matched_direct = (
            merged["median_income"].notna().sum()
            if "median_income" in merged.columns
            else 0
        )
        pct_direct = (n_matched_direct / n_total * 100) if n_total > 0 else 0

        logger.info(
            "Merged census data: %d/%d observations matched directly (%.1f%%)",
            n_matched_direct,
            n_total,
            pct_direct,
        )

        merged = self._impute_missing_census_with_county_medians(merged, census)

        n_after = (
            merged["median_income"].notna().sum()
            if "median_income" in merged.columns
            else 0
        )
        if n_total > 0:
            logger.info(
                "After county-median imputation: %d/%d observations have census covariates (%.1f%%)",
                n_after,
                n_total,
                100.0 * n_after / n_total,
            )

        if "median_income" in merged.columns and merged["median_income"].isna().any():
            bad = merged["median_income"].isna()
            logger.warning(
                "Census covariates still missing for %d rows after imputation. "
                "Sample tract_geoid: %s",
                int(bad.sum()),
                merged.loc[bad, "tract_geoid"].drop_duplicates().head(10).tolist(),
            )

        return merged

    def _impute_missing_census_with_county_medians(
        self, merged: pd.DataFrame, census: pd.DataFrame
    ) -> pd.DataFrame:
        """Fill missing ACS columns using the median among tracts in the same county."""
        cov_cols = [
            c
            for c in _CENSUS_COVARIATE_COLS
            if c in merged.columns and c in census.columns
        ]
        if not cov_cols:
            return merged

        need = merged[cov_cols].isna().any(axis=1)
        if not need.any():
            return merged

        census_work = census.copy()
        census_work["_county_merge"] = _county_fips_from_census_row(census_work)
        county_medians = (
            census_work.dropna(subset=["_county_merge"])
            .groupby("_county_merge", observed=True)[cov_cols]
            .median()
        )
        global_medians = census_work[cov_cols].median()

        panel_county = _county_fips_from_panel_geoid(merged["tract_geoid"])
        n_cells = 0
        for col in cov_cols:
            fill_co = panel_county.map(county_medians[col])
            before = merged[col].isna()
            merged[col] = merged[col].fillna(fill_co)
            merged[col] = merged[col].fillna(global_medians[col])
            n_cells += int((before & merged[col].notna()).sum())

        n_rows = int(need.sum())
        logger.info(
            "County-median imputation (fallback: statewide median): filled %d cell-values "
            "for tract-month rows missing direct ACS match (%d rows had at least one missing covariate).",
            n_cells,
            n_rows,
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
