"""Aggregates zip codes to tract for time series rental data"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from scipy.stats import linregress
from sklearn.neighbors import NearestNeighbors

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TrendMatchingProcessor(DataProcessor):
    """Processor for time series rental data, zip codes to tracts aggregation.

    Args:
        k_neighbors: The number of neighbors to use for the nearest neighbors model.
        min_pre_periods: The minimum number of pre-treatment periods to use for the trend matching.
    """

    def __init__(
        self,
        output_dir: str | None = None,
        k_neighbors: int = 3,
        min_pre_periods: int = 6,
    ) -> None:
        """Initialize the zip to tract processor."""
        super().__init__(
            "trend_matching_data",
            "Perform trend matching on the rental data",
        )
        self.k_neighbors = k_neighbors
        self.min_pre_periods = min_pre_periods
        self.output_dir = output_dir or "/project/output"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform trend matching on the rental data."""
        # Get the data from context
        did_panel = context["did_panel_data"]

        first_treatment = (
            did_panel[["tract_geoid", "first_prohibition_date"]]
            .drop_duplicates()
            .set_index("tract_geoid")["first_prohibition_date"]
        )
        panel_min_month = did_panel["month"].min()

        # Step 1: Calculate pre-treatment trends
        rows = []
        for tract_geoid, group in did_panel.groupby("tract_geoid"):
            ft = first_treatment.get(tract_geoid)
            pre = group[group["month"] < ft] if pd.notna(ft) else group
            if len(pre) < self.min_pre_periods:
                continue
            months_numeric = (pre["month"] - panel_min_month).dt.total_seconds() / (
                30 * 24 * 3600
            )
            slope, _, _, _, _ = linregress(months_numeric, pre["rental_price"])
            ever_treated = (
                (group["treated"].max() > 0) if "treated" in group.columns else False
            )
            rows.append(
                {
                    "tract_geoid": tract_geoid,
                    "pre_trend_slope": slope,
                    "ever_treated": ever_treated,
                }
            )

        trends = pd.DataFrame(rows)
        if len(trends) == 0:
            raise ValueError(
                "No tracts have enough pre-treatment months. Try reducing min_pre_periods "
                "or using a longer panel."
            )

        # Step 2: Match treated to never-treated controls
        treated_trends = trends[trends["ever_treated"]]
        control_trends = trends[~trends["ever_treated"]]
        if len(control_trends) == 0:
            raise ValueError("No never-treated tracts available for matching.")
        if len(treated_trends) == 0:
            logger.warning("No treated tracts; returning full panel.")
            return {"did_panel_data": did_panel}

        k = min(self.k_neighbors, len(control_trends))
        nn = NearestNeighbors(n_neighbors=k, metric="euclidean")
        nn.fit(control_trends[["pre_trend_slope"]].values)

        matching_rows = []
        for _, row in treated_trends.iterrows():
            distances, indices = nn.kneighbors([[row["pre_trend_slope"]]])
            for j in range(k):
                ctrl_idx = indices[0][j]
                ctrl_tract = control_trends.iloc[ctrl_idx]["tract_geoid"]
                matching_rows.append(
                    {
                        "treated_tract": row["tract_geoid"],
                        "control_tract": ctrl_tract,
                        "distance": distances[0][j],
                    }
                )
        matching = pd.DataFrame(matching_rows)

        # Step 3: Create matched sample
        matched_tracts = pd.concat(
            [matching["treated_tract"], matching["control_tract"]]
        ).unique()
        matched_panel = did_panel[did_panel["tract_geoid"].isin(matched_tracts)].copy()

        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "trend_matching_analysis.csv"

        matched_panel.to_csv(output_path, index=False)

        return {
            "did_panel_data": matched_panel,
        }
