"""Trend-matching processor for Difference-in-Differences analysis.

1. Computes pre-treatment rental price trends (slopes) for each tract
2. Matches treated tracts to never-treated controls on pre-treatment slope
3. Filters the DiD panel to the matched set of tracts
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from scipy.stats import linregress
from sklearn.neighbors import NearestNeighbors

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TrendMatchingProcessor(DataProcessor):
    """Match treated tracts to controls on pre-treatment rent trends."""

    def __init__(
        self,
        k_neighbors: int = 3,
        min_pre_periods: int = 6,
    ) -> None:
        """Initialize the trend-matching processor.

        Args:
            k_neighbors: Number of nearest neighbors to match to each treated tract.
            min_pre_periods: Minimum number of pre-treatment months required
                to estimate a trend for a tract.
        """
        super().__init__(
            "trend_matching",
            "Match treated tracts to never-treated controls on pre-treatment rent trends",
        )
        self.k_neighbors = k_neighbors
        self.min_pre_periods = min_pre_periods
        self.required_data = ["did_panel"]

    def _compute_pre_trends(self, did_panel: pd.DataFrame) -> pd.DataFrame:
        """Compute pre-treatment rental price trends for each tract."""
        # Identify ever-treated tracts
        ever_treated_series = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_tracts = ever_treated_series[ever_treated_series == 1].index

        # Define global pre-treatment period (before any tract is treated)
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
        if pd.isna(first_treatment):
            raise ValueError(
                "No treated observations found in did_panel; cannot perform trend matching."
            )

        pre_period = did_panel[did_panel["month"] < first_treatment]

        records: list[dict[str, Any]] = []

        for tract_id, tract_df in pre_period.groupby("tract_geoid"):
            if len(tract_df) < self.min_pre_periods:
                continue

            # Convert month to numeric (months since first observation in this tract)
            time_delta = tract_df["month"] - tract_df["month"].min()
            months_numeric = time_delta.dt.total_seconds() / (30 * 24 * 3600)

            result = linregress(months_numeric, tract_df["rental_price"])
            records.append(
                {
                    "tract_geoid": tract_id,
                    "pre_trend_slope": result.slope,
                    "ever_treated": tract_id in ever_treated_tracts,
                }
            )

        if not records:
            raise ValueError(
                "No tracts have sufficient pre-treatment periods to estimate trends. "
                "Try reducing 'min_pre_periods' or using a longer panel."
            )

        trends_df = pd.DataFrame.from_records(records)
        logger.info(
            "Computed pre-treatment trends for %d tracts "
            "(min_pre_periods=%d, k_neighbors=%d)",
            len(trends_df),
            self.min_pre_periods,
            self.k_neighbors,
        )
        return trends_df

    def _match_tracts(self, trends_df: pd.DataFrame) -> pd.DataFrame:
        """Match treated tracts to never-treated controls using k-NN on slopes."""
        treated_trends = trends_df[trends_df["ever_treated"]].copy()
        control_trends = trends_df[~trends_df["ever_treated"]].copy()

        if treated_trends.empty:
            raise ValueError(
                "No ever-treated tracts with valid pre-treatment trends to match."
            )
        if control_trends.empty:
            raise ValueError(
                "No never-treated tracts with valid pre-treatment trends to match."
            )

        n_neighbors = min(self.k_neighbors, len(control_trends))

        nn = NearestNeighbors(n_neighbors=n_neighbors)
        nn.fit(control_trends[["pre_trend_slope"]].to_numpy())

        matches: list[dict[str, Any]] = []

        for _, treated_row in treated_trends.iterrows():
            slope = treated_row["pre_trend_slope"]
            distances, indices = nn.kneighbors([[slope]])

            for dist, idx in zip(distances[0], indices[0]):
                control_row = control_trends.iloc[idx]
                matches.append(
                    {
                        "treated_tract": treated_row["tract_geoid"],
                        "control_tract": control_row["tract_geoid"],
                        "treated_slope": treated_row["pre_trend_slope"],
                        "control_slope": control_row["pre_trend_slope"],
                        "distance": float(dist),
                    }
                )

        matches_df = pd.DataFrame.from_records(matches)
        logger.info(
            "Created %d treated-control matches using %d neighbors.",
            len(matches_df),
            n_neighbors,
        )
        return matches_df

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the trend-matching processor."""
        did_panel = context["did_panel"]

        logger.info("Starting trend matching on DiD panel (n=%d)", len(did_panel))

        trends_df = self._compute_pre_trends(did_panel)
        matches_df = self._match_tracts(trends_df)

        matched_tracts = set(matches_df["treated_tract"]) | set(
            matches_df["control_tract"]
        )
        logger.info("Matched sample contains %d unique tracts.", len(matched_tracts))

        matched_panel = did_panel[did_panel["tract_geoid"].isin(matched_tracts)].copy()
        logger.info(
            "Filtered DiD panel from %d to %d observations after trend matching.",
            len(did_panel),
            len(matched_panel),
        )

        return {
            "did_panel": matched_panel,
            "trend_matching_trends": trends_df,
            "trend_matching_matches": matches_df,
        }

