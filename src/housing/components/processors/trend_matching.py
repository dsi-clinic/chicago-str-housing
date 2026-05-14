"""Trend matching processor for DiD analysis.

This module matches treated tracts to never-treated control tracts
based on pre-treatment rent trends to improve comparability.
"""

import logging
from typing import Any

import pandas as pd
from scipy.stats import linregress
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

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
        matching_features: tuple[str, ...] = ("pre_trend_slope", "avg_pre_rent"),
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
        self.matching_features = matching_features

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
                "No tracts have at least %d months of pre-treatment data. "
                "First treatment in panel is %s; reduce min_pre_periods (e.g. to 6) "
                "or use a panel with longer pre-treatment history."
                % (self.min_pre_periods, first_treatment)
            )

        # Step 2: Match treated to control tracts
        matching_info = self._match_tracts(trends_df)

        # Step 3: Create matched sample
        matched_panel = self._create_matched_sample(did_panel, matching_info)

        matching_diagnostics = self._compute_matching_diagnostics(
            trends_df=trends_df,
            matching_info=matching_info,
        )

        # Log results
        self._log_matching_results(
            trends_df,
            matching_info,
            matched_panel,
            matching_diagnostics,
        )

        return {
            "did_panel": matched_panel,  # Update did_panel for subsequent components
            "did_panel_matched": matched_panel,  # Keep for reference
            "matching_info": matching_info,
            "trends_df": trends_df,
            "matching_diagnostics": matching_diagnostics,
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

        missing_features = [
            feature
            for feature in self.matching_features
            if feature not in trends_df.columns
        ]
        if missing_features:
            msg = f"Missing matching feature(s): {missing_features}"
            raise ValueError(msg)

        scaler = StandardScaler()
        control_features = control_trends[list(self.matching_features)].to_numpy()
        treated_features = treated_trends[list(self.matching_features)].to_numpy()
        control_features_scaled = scaler.fit_transform(control_features)
        treated_features_scaled = scaler.transform(treated_features)

        # Fit k-nearest neighbors on control tracts
        nn = NearestNeighbors(
            n_neighbors=min(self.k_neighbors, len(control_trends)),
            metric="euclidean",
        )
        nn.fit(control_features_scaled)

        # Find matches for each treated tract
        matching_records = []

        for i_treated, (_idx, treated_row) in enumerate(treated_trends.iterrows()):
            # Find k nearest neighbors
            distances, indices = nn.kneighbors([treated_features_scaled[i_treated]])

            for i, (dist, control_idx) in enumerate(zip(distances[0], indices[0])):
                # Apply caliper if specified
                if self.caliper is not None and dist > self.caliper:
                    continue

                control_tract = control_trends.iloc[control_idx]
                record = {
                    "treated_tract": treated_row["tract_geoid"],
                    "control_tract": control_tract["tract_geoid"],
                    "distance": dist,
                    "match_rank": i + 1,
                }
                for feature in self.matching_features:
                    record[f"treated_{feature}"] = treated_row[feature]
                    record[f"control_{feature}"] = control_tract[feature]
                matching_records.append(record)

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

    def _compute_matching_diagnostics(
        self,
        trends_df: pd.DataFrame,
        matching_info: pd.DataFrame,
    ) -> dict[str, Any]:
        """Compute summary diagnostics for balance and control reuse."""
        treated_trends = trends_df[trends_df["ever_treated"] == 1].copy()
        control_trends = trends_df[trends_df["ever_treated"] == 0].copy()
        matched_control_ids = matching_info["control_tract"].unique()
        matched_controls = control_trends[
            control_trends["tract_geoid"].isin(matched_control_ids)
        ].copy()
        control_reuse = (
            matching_info.groupby("control_tract")["treated_tract"]
            .nunique()
            .rename("n_treated_matches")
            .reset_index()
        )

        diagnostics: dict[str, Any] = {
            "matching_features": ",".join(self.matching_features),
            "matched_treated_tracts": int(matching_info["treated_tract"].nunique()),
            "matched_control_tracts": int(matching_info["control_tract"].nunique()),
            "matched_pairs": int(len(matching_info)),
            "distance_mean": float(matching_info["distance"].mean()),
            "distance_median": float(matching_info["distance"].median()),
            "distance_p90": float(matching_info["distance"].quantile(0.90)),
            "distance_p95": float(matching_info["distance"].quantile(0.95)),
            "distance_max": float(matching_info["distance"].max()),
            "control_reuse_mean": float(control_reuse["n_treated_matches"].mean()),
            "control_reuse_median": float(control_reuse["n_treated_matches"].median()),
            "control_reuse_p90": float(control_reuse["n_treated_matches"].quantile(0.90)),
            "control_reuse_p95": float(control_reuse["n_treated_matches"].quantile(0.95)),
            "control_reuse_max": int(control_reuse["n_treated_matches"].max()),
            "control_reuse_table": control_reuse,
        }

        for feature in self.matching_features:
            diagnostics[f"smd_{feature}_before"] = self._standardized_mean_difference(
                treated_trends[feature],
                control_trends[feature],
            )
            diagnostics[f"smd_{feature}_after"] = self._standardized_mean_difference(
                treated_trends[feature],
                matched_controls[feature],
            )

        return diagnostics

    @staticmethod
    def _standardized_mean_difference(
        treated: pd.Series,
        control: pd.Series,
    ) -> float:
        treated_var = treated.var(ddof=1)
        control_var = control.var(ddof=1)
        pooled_sd = ((treated_var + control_var) / 2) ** 0.5
        if pooled_sd == 0 or pd.isna(pooled_sd):
            return float("nan")
        return float((treated.mean() - control.mean()) / pooled_sd)

    def _log_matching_results(
        self,
        trends_df: pd.DataFrame,
        matching_info: pd.DataFrame,
        matched_panel: pd.DataFrame,
        matching_diagnostics: dict[str, Any],
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
        logger.info(
            "  Distance p95: %.4f",
            matching_diagnostics["distance_p95"],
        )
        logger.info("  Max distance: %.4f", matching_info["distance"].max())
        logger.info(
            "  Control reuse max: %d",
            matching_diagnostics["control_reuse_max"],
        )
        for feature in self.matching_features:
            logger.info(
                "  SMD %s: before %.3f, after %.3f",
                feature,
                matching_diagnostics.get(f"smd_{feature}_before"),
                matching_diagnostics.get(f"smd_{feature}_after"),
            )

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
