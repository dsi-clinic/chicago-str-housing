"""Trend matching processor for DiD analysis.

This module matches treated tracts to never-treated control tracts based on
pre-treatment rental price trends to improve comparability.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.neighbors import NearestNeighbors

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TrendMatchingProcessor(DataProcessor):
    """Match treated tracts to never-treated controls based on pre-treatment trends.

    This processor:
    1. Calculates pre-treatment rental price trends for each tract
    2. Matches treated tracts to k nearest never-treated tracts by trend slope
    3. Filters the did_panel to only include matched tracts
    """

    def __init__(self, k_neighbors: int = 3, min_pre_periods: int = 6) -> None:
        """Initialize the trend matching processor.

        Args:
            k_neighbors: Number of nearest neighbors to match for each treated tract
            min_pre_periods: Minimum number of pre-treatment months required
        """
        super().__init__(
            "trend_matching",
            "Match treated tracts to controls based on pre-treatment trends",
        )
        self.k_neighbors = k_neighbors
        self.min_pre_periods = min_pre_periods
        self.required_data = ["did_panel"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Calculate pre-treatment trends, match tracts, and filter panel.

        Args:
            context: Pipeline context containing:
                - did_panel: DataFrame with tract_geoid, month, rental_price,
                  first_prohibition_date, treated, months_since_treatment

        Returns:
            Dictionary with 'did_panel' key containing filtered panel DataFrame
        """
        did_panel = context["did_panel"].copy()

        # Ensure month is datetime
        if not pd.api.types.is_datetime64_any_dtype(did_panel["month"]):
            did_panel["month"] = pd.to_datetime(did_panel["month"])

        # Step 1: Calculate pre-treatment trends
        logger.info("Calculating pre-treatment trends...")
        trends_df = self._calculate_pre_treatment_trends(did_panel)

        if len(trends_df) == 0:
            raise ValueError(
                f"No tracts have at least {self.min_pre_periods} months of "
                "pre-treatment data. Consider reducing min_pre_periods or using "
                "a longer panel."
            )

        # Step 2: Match treated to never-treated tracts
        logger.info("Matching treated tracts to controls...")
        matching_df = self._match_tracts(trends_df)

        # Step 3: Create matched sample
        logger.info("Creating matched sample...")
        matched_panel = self._create_matched_sample(did_panel, matching_df)

        logger.info(
            "Matched sample: %d treated tracts, %d control tracts, %d total tracts",
            matching_df["treated_tract"].nunique(),
            matching_df["control_tract"].nunique(),
            matched_panel["tract_geoid"].nunique(),
        )

        return {"did_panel": matched_panel}

    def _calculate_pre_treatment_trends(
        self, did_panel: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate pre-treatment rental price trends for each tract.

        Args:
            did_panel: DiD panel DataFrame

        Returns:
            DataFrame with columns: tract_geoid, pre_trend_slope, ever_treated
        """
        # Identify ever-treated vs never-treated tracts
        ever_treated = did_panel.groupby("tract_geoid")["treated"].max()
        ever_treated_map = ((ever_treated > 0).astype(int)).to_dict()

        # Get first treatment date across all tracts
        first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()

        if pd.isna(first_treatment):
            raise ValueError("No treated observations found in did_panel")

        trends_list = []

        # Convert month to numeric (months since panel start)
        min_month = did_panel["month"].min()
        did_panel["month_numeric"] = (
            (did_panel["month"] - min_month).dt.total_seconds()
            / (30 * 24 * 3600)
        )

        # Loop over tracts
        for tract_id in did_panel["tract_geoid"].unique():
            tract_data = did_panel[did_panel["tract_geoid"] == tract_id].copy()

            # Get first_prohibition_date for this tract
            first_prohibition = tract_data["first_prohibition_date"].iloc[0]

            # Define pre-treatment period
            if pd.isna(first_prohibition):
                # Never-treated tract: use all months
                pre_period = tract_data.copy()
            else:
                # Treated tract: use months before first_prohibition_date
                pre_period = tract_data[tract_data["month"] < first_prohibition].copy()

            # Require minimum pre-period months
            if len(pre_period) < self.min_pre_periods:
                continue

            # Fit linear regression: rental_price ~ month_numeric
            if len(pre_period) < 2:
                continue

            slope, intercept, r_value, p_value, std_err = stats.linregress(
                pre_period["month_numeric"], pre_period["rental_price"]
            )

            trends_list.append(
                {
                    "tract_geoid": tract_id,
                    "pre_trend_slope": slope,
                    "ever_treated": ever_treated_map.get(tract_id, 0),
                }
            )

        trends_df = pd.DataFrame(trends_list)

        logger.info(
            "Calculated trends for %d tracts (%d treated, %d never-treated)",
            len(trends_df),
            trends_df["ever_treated"].sum(),
            (trends_df["ever_treated"] == 0).sum(),
        )

        return trends_df

    def _match_tracts(self, trends_df: pd.DataFrame) -> pd.DataFrame:
        """Match treated tracts to never-treated controls by pre-treatment trend.

        Args:
            trends_df: DataFrame with tract_geoid, pre_trend_slope, ever_treated

        Returns:
            DataFrame with columns: treated_tract, control_tract, distance
        """
        # Split into treated and control
        treated_trends = trends_df[trends_df["ever_treated"] == 1].copy()
        control_trends = trends_df[trends_df["ever_treated"] == 0].copy()

        if len(treated_trends) == 0:
            raise ValueError("No treated tracts found for matching")
        if len(control_trends) == 0:
            raise ValueError("No never-treated control tracts found for matching")

        # Fit NearestNeighbors on control slopes
        # NearestNeighbors expects 2D array
        control_slopes = control_trends[["pre_trend_slope"]].values
        nn = NearestNeighbors(n_neighbors=min(self.k_neighbors, len(control_trends)))
        nn.fit(control_slopes)

        # Match each treated tract
        matching_list = []
        for _, treated_row in treated_trends.iterrows():
            treated_slope = treated_row["pre_trend_slope"]
            treated_tract = treated_row["tract_geoid"]

            # Find k nearest neighbors
            distances, indices = nn.kneighbors([[treated_slope]])

            # Get matched control tracts
            for dist, idx in zip(distances[0], indices[0]):
                control_tract = control_trends.iloc[idx]["tract_geoid"]
                matching_list.append(
                    {
                        "treated_tract": treated_tract,
                        "control_tract": control_tract,
                        "distance": dist,
                    }
                )

        matching_df = pd.DataFrame(matching_list)

        logger.info(
            "Matched %d treated tracts to %d control tracts (%d pairs)",
            matching_df["treated_tract"].nunique(),
            matching_df["control_tract"].nunique(),
            len(matching_df),
        )

        return matching_df

    def _create_matched_sample(
        self, did_panel: pd.DataFrame, matching_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Filter did_panel to only include matched tracts.

        Args:
            did_panel: Full DiD panel DataFrame
            matching_df: Matching DataFrame with treated_tract, control_tract

        Returns:
            Filtered did_panel containing only matched tracts
        """
        # Get unique tract IDs from matching
        matched_tracts = set(matching_df["treated_tract"].unique()) | set(
            matching_df["control_tract"].unique()
        )

        # Filter panel
        matched_panel = did_panel[did_panel["tract_geoid"].isin(matched_tracts)].copy()

        # Drop the temporary month_numeric column if it exists
        if "month_numeric" in matched_panel.columns:
            matched_panel = matched_panel.drop(columns=["month_numeric"])

        return matched_panel
