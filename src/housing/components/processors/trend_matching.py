"""Trend matching processor.

Computes pre-treatment rental price trend slopes for each tract, matches each treated tract
to k nearest never-treated tracts by slope distance, and returns a filtered DiD panel
restricted to the matched tracts along with the match table.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import linregress
from sklearn.neighbors import NearestNeighbors

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TrendMatchingProcessor(DataProcessor):
    """Match treated tracts to controls based on pre-treatment trend similarity."""

    def __init__(self, min_pre_periods: int = 6, k_neighbors: int = 3) -> None:
        """Initialize the trend matching processor.

        Args:
            min_pre_periods: Minimum number of pre-treatment periods required for treated
                tracts to be eligible.
            k_neighbors: Number of nearest control neighbors to match to each treated tract.
        """
        super().__init__(
            "trend_matching",
            "match treated tracts to controls with similar pre-treatment trends",
        )
        self.min_pre_periods = min_pre_periods
        self.k_neighbors = k_neighbors

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run trend matching and return matched panel + match table."""
        # Get data from context
        did_panel = context["did_panel"]

        panel = did_panel.copy()

        # Identify ever-treated tracts (any treated==1 over time)
        ever_treated = panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated[ever_treated == 1].index

        panel["ever_treated"] = (
            panel["tract_geoid"].isin(ever_treated_tracts).astype(int)
        )

        # Convert month to numeric scale (approx. months since first observed month)
        panel["month_numeric"] = (
            panel["month"] - panel["month"].min()
        ).dt.total_seconds() / (30 * 24 * 3600)

        # Eligible tracts: treated must have at least `min_pre_periods` months pre-treatment;
        # never-treated always eligible.
        min_event_time = panel.groupby("tract_geoid")["months_since_treatment"].min()

        valid_tracts = min_event_time[
            (min_event_time <= self.min_pre_periods * -1) | (min_event_time.isna())
        ].index

        panel_filtered = panel.loc[panel["tract_geoid"].isin(valid_tracts)]

        # Helper: compute slope per tract using treated-pre period vs never-treated full period
        def get_tract_slope(group: pd.DataFrame) -> float:
            first_treatment_date = panel.loc[panel["treated"] == 1]["month"].min()
            if group["ever_treated"].iloc[0] == 1:
                # Treated tract → true pre-period
                pre = group[group["months_since_treatment"] < 0]
            else:
                # Never-treated → use entire time span
                pre = group[group["month"] < first_treatment_date]
            return linregress(pre["month_numeric"], pre["rental_price"]).slope

        slopes = panel_filtered.groupby("tract_geoid").apply(get_tract_slope)

        # Build slope table (one row per tract)
        pre_trend_slopes = panel_filtered.groupby("tract_geoid")[["ever_treated"]].min()
        pre_trend_slopes["pre_trend_slope"] = slopes

        n_nan_slopes = int(pre_trend_slopes["pre_trend_slope"].isna().sum())
        if n_nan_slopes > 0:
            logger.warning(
                "TrendMatching: %d/%d tracts have NaN slope (insufficient or invalid pre data).",
                n_nan_slopes,
                len(pre_trend_slopes),
            )

        treated_trends = pre_trend_slopes[pre_trend_slopes["ever_treated"] == 1].copy()
        control_trends = pre_trend_slopes[pre_trend_slopes["ever_treated"] == 0].copy()

        k = min(self.k_neighbors, len(control_trends))

        # If there are no controls, produce an empty match df (avoid crashing downstream)
        if k == 0:
            matches = pd.DataFrame(
                columns=["treated_tract", "control_tract", "distance"]
            )
        else:
            control_slopes = control_trends["pre_trend_slope"].to_numpy().reshape(-1, 1)

            nn = NearestNeighbors(n_neighbors=k, metric="euclidean")
            nn.fit(control_slopes)

            treated_ids = treated_trends.index.to_numpy()
            treated_slopes = treated_trends["pre_trend_slope"].to_numpy().reshape(-1, 1)

            # kneighbors on all treated tracts
            distances, indices = nn.kneighbors(treated_slopes)

            control_ids = control_trends.index.to_numpy()

            # Build one row per treated-control neighbor
            matches = pd.DataFrame(
                {
                    "treated_tract": np.repeat(treated_ids, k),
                    "control_tract": control_ids[indices.reshape(-1)],
                    "distance": distances.reshape(-1),
                }
            )

            logger.info(
                "TrendMatching: produced %d matches (%d treated x %d neighbors).",
                len(matches),
                len(treated_ids),
                k,
            )

        # Collect all unique matched tract IDs
        n_matched_treated = len(matches["treated_tract"].unique())
        n_matched_control = len(matches["control_tract"].unique())
        matched_tracts = pd.unique(
            matches[["treated_tract", "control_tract"]].to_numpy().ravel()
        )

        logger.info(
            "TrendMatching: matched tracts=%d (treated=%d, controls=%d).",
            len(matched_tracts),
            n_matched_treated,
            n_matched_control,
        )

        # Filter original DiD panel
        did_panel_matched = did_panel[
            did_panel["tract_geoid"].isin(matched_tracts)
        ].copy()

        return {
            "did_panel_matched": did_panel_matched,
            "tract_trend_matches": matches,  # return matched pairs
        }
