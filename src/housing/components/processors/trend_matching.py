"""Trend matching processor for DiD analysis.

This module matches treated tracts to never-treated control tracts
based on pre-treatment rent trends to improve comparability.
"""

import logging
from typing import Any

import pandas as pd
from scipy.stats import linregress
from sklearn.neighbors import NearestNeighbors

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TrendMatchingProcessor(DataProcessor):
    """Match treated tracts to control tracts based on pre-treatment trends.

    This processor:
    1. Calculates pre-treatment rent trends (slopes) for all tracts
    2. Matches each treated tract to k nearest never-treated tracts
    3. Creates a matched sample for more comparable DiD analysis

    This helps address violations of parallel trends by ensuring
    treated and control groups have similar pre-treatment trajectories.
    """

    def __init__(
        self,
        k_neighbors: int = 3,
        min_pre_periods: int = 6,
        caliper: float | None = None,
    ) -> None:
        """Initialize the trend matching processor.

        Args:
            k_neighbors: Number of control matches per treated tract
            min_pre_periods: Minimum pre-treatment months required
            caliper: Maximum allowed difference in trend slopes (None = no limit)
        """
        super().__init__(
            "trend_matching",
            "Match treated tracts to controls based on pre-treatment trends",
        )
        self.required_data = ["did_panel"]
        self.k_neighbors = k_neighbors
        self.min_pre_periods = min_pre_periods
        self.caliper = caliper

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform trend matching and create matched sample.

        Required context keys:
            - did_panel: DataFrame with DiD panel data

        Returns:
            Dictionary with:
            - did_panel_matched: Matched sample panel data
            - matching_info: DataFrame with matching details
            - trends_df: Pre-treatment trends for all tracts
        """
        did_panel = context["did_panel"].copy()

        logger.info("Performing trend matching...")
        logger.info("  K-neighbors: %d", self.k_neighbors)
        logger.info("  Min pre-periods: %d", self.min_pre_periods)

        # Step 1: Calculate pre-treatment trends
        trends_df = self._calculate_pre_trends(did_panel)

        if trends_df.empty:
            first_treatment = did_panel.loc[did_panel["treated"] == 1, "month"].min()
            raise ValueError(
                f"No tracts have at least {self.min_pre_periods} months of pre-treatment data. "
                f"First treatment in panel is {first_treatment}; reduce min_pre_periods (e.g. to 6) "
                "or use a panel with longer pre-treatment history."
            )

        # Step 2: Match treated to control tracts
        matching_info = self._match_tracts(trends_df)

        # Step 3: Create matched sample
        matched_panel = self._create_matched_sample(did_panel, matching_info)

        # Log results
        self._log_matching_results(trends_df, matching_info, matched_panel)

        return {
            "did_panel": matched_panel,  # Update did_panel for subsequent components
            "did_panel_matched": matched_panel,  # Keep for reference
            "matching_info": matching_info,
            "trends_df": trends_df,
        }

    def _calculate_pre_trends(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate pre-treatment rent trends for each tract."""
        # Identify first treatment date in sample
        first_treatment = df.loc[df["treated"] == 1, "month"].min()

        # Get all unique tracts
        all_tracts = df["tract_geoid"].unique()

        pre_trends = []

        for tract_id in all_tracts:
            tract_data = df[df["tract_geoid"] == tract_id].copy()

            # Get pre-treatment period
            pre_data = tract_data[tract_data["month"] < first_treatment]

            if len(pre_data) < self.min_pre_periods:
                # Not enough pre-treatment data
                continue

            # Calculate linear trend: rent ~ time
            pre_data = pre_data.sort_values("month")
            months_numeric = (
                pre_data["month"] - pre_data["month"].min()
            ).dt.total_seconds() / (30 * 24 * 3600)  # Convert to months as float

            try:
                slope, intercept, r_value, p_value, std_err = linregress(
                    months_numeric, pre_data["rental_price"]
                )

                # Also calculate average pre-treatment rent
                avg_pre_rent = pre_data["rental_price"].mean()

                pre_trends.append(
                    {
                        "tract_geoid": tract_id,
                        "pre_trend_slope": slope,  # $ per month
                        "pre_trend_intercept": intercept,
                        "pre_trend_r_squared": r_value**2,
                        "pre_trend_p_value": p_value,
                        "avg_pre_rent": avg_pre_rent,
                        "n_pre_periods": len(pre_data),
                        "ever_treated": tract_data["ever_treated"].iloc[0]
                        if "ever_treated" in tract_data.columns
                        else (tract_data["treated"].max() > 0),
                    }
                )
            except Exception as e:
                logger.warning(
                    "  Failed to calculate trend for tract %s: %s", tract_id, e
                )
                continue

        trends_df = pd.DataFrame(pre_trends)

        logger.info("  Calculated trends for %d tracts", len(trends_df))
        logger.info(
            "    Treated: %d, Never-treated: %d",
            (trends_df["ever_treated"] == 1).sum(),
            (trends_df["ever_treated"] == 0).sum(),
        )

        return trends_df

    def _match_tracts(self, trends_df: pd.DataFrame) -> pd.DataFrame:
        """Match treated tracts to control tracts using k-nearest neighbors."""
        treated_trends = trends_df[trends_df["ever_treated"] == 1].copy()
        control_trends = trends_df[trends_df["ever_treated"] == 0].copy()

        if len(treated_trends) == 0:
            raise ValueError("No treated tracts found for matching")
        if len(control_trends) == 0:
            raise ValueError("No control tracts found for matching")

        logger.info(
            "  Matching %d treated to %d control tracts",
            len(treated_trends),
            len(control_trends),
        )

        # Prepare matching variables (just trend slope for now)
        # Could extend to multiple dimensions
        matching_var = "pre_trend_slope"

        # Fit k-nearest neighbors on control tracts
        nn = NearestNeighbors(
            n_neighbors=min(self.k_neighbors, len(control_trends)),
            metric="euclidean",
        )
        nn.fit(control_trends[[matching_var]].values)

        # Find matches for each treated tract
        matching_records = []

        for _idx, treated_row in treated_trends.iterrows():
            treated_slope = treated_row[matching_var]

            # Find k nearest neighbors
            distances, indices = nn.kneighbors([[treated_slope]])

            for i, (dist, control_idx) in enumerate(zip(distances[0], indices[0])):
                # Apply caliper if specified
                if self.caliper is not None and dist > self.caliper:
                    continue

                control_tract = control_trends.iloc[control_idx]

                matching_records.append(
                    {
                        "treated_tract": treated_row["tract_geoid"],
                        "control_tract": control_tract["tract_geoid"],
                        "treated_slope": treated_slope,
                        "control_slope": control_tract[matching_var],
                        "distance": dist,
                        "match_rank": i + 1,
                    }
                )

        matching_info = pd.DataFrame(matching_records)

        logger.info("  Created %d matched pairs", len(matching_info))

        return matching_info

    def _create_matched_sample(
        self, did_panel: pd.DataFrame, matching_info: pd.DataFrame
    ) -> pd.DataFrame:
        """Create panel data with only matched tracts."""
        # Get all matched tract IDs
        treated_tracts = matching_info["treated_tract"].unique()
        control_tracts = matching_info["control_tract"].unique()

        matched_tracts = set(treated_tracts) | set(control_tracts)

        # Filter panel to matched tracts
        matched_panel = did_panel[did_panel["tract_geoid"].isin(matched_tracts)].copy()

        # Add matching indicator
        matched_panel["matched_treated"] = (
            matched_panel["tract_geoid"].isin(treated_tracts).astype(int)
        )
        matched_panel["matched_control"] = (
            matched_panel["tract_geoid"].isin(control_tracts).astype(int)
        )

        return matched_panel

    def _log_matching_results(
        self,
        trends_df: pd.DataFrame,
        matching_info: pd.DataFrame,
        matched_panel: pd.DataFrame,
    ) -> None:
        """Log summary of matching results."""
        logger.info("\n" + "=" * 60)
        logger.info("Trend Matching Results")
        logger.info("=" * 60)

        treated_trends = trends_df[trends_df["ever_treated"] == 1]
        control_trends = trends_df[trends_df["ever_treated"] == 0]

        logger.info("\nPre-Treatment Trend Statistics:")
        logger.info("  Treated tracts:")
        logger.info(
            "    Mean slope: $%.2f/month", treated_trends["pre_trend_slope"].mean()
        )
        logger.info(
            "    Std slope: $%.2f/month", treated_trends["pre_trend_slope"].std()
        )
        logger.info("  Control tracts:")
        logger.info(
            "    Mean slope: $%.2f/month", control_trends["pre_trend_slope"].mean()
        )
        logger.info(
            "    Std slope: $%.2f/month", control_trends["pre_trend_slope"].std()
        )

        logger.info("\nMatching Quality:")
        logger.info(
            "  Matched treated tracts: %d", matching_info["treated_tract"].nunique()
        )
        logger.info(
            "  Matched control tracts: %d", matching_info["control_tract"].nunique()
        )
        logger.info("  Average distance: %.4f", matching_info["distance"].mean())
        logger.info("  Max distance: %.4f", matching_info["distance"].max())

        logger.info("\nMatched Sample:")
        logger.info("  Total tracts: %d", matched_panel["tract_geoid"].nunique())
        logger.info(
            "  Treated tracts: %d",
            matched_panel.loc[
                matched_panel["matched_treated"] > 0, "tract_geoid"
            ].nunique(),
        )
        logger.info(
            "  Control tracts: %d",
            matched_panel.loc[
                matched_panel["matched_control"] > 0, "tract_geoid"
            ].nunique(),
        )
        logger.info("  Observations: %d", len(matched_panel))
