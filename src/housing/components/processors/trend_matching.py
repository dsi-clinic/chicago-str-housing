"""Treatment indicator processor for difference-in-differences analysis.

This module creates treatment indicators and relative time variables for
tract-level rental panel data, enabling difference-in-differences (DiD)
analysis of short-term rental (STR) prohibition effects on rental prices.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import linregress
from sklearn.neighbors import NearestNeighbors

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TrendMatchingProcessor(DataProcessor):
    """Create treatment indicators for difference-in-differences analysis.

    This processor merges tract-level rental panel data with treatment dates
    (STR prohibition dates) and creates:
    1. Binary treatment indicator (`treated`): 0 before treatment, 1 after
    2. Relative time variable (`months_since_treatment`): months before/after
       treatment date

    Args:
    - output_dir: Optional output directory for visualizations

    Returns:
    - `did_panel`: DataFrame with added `treated` and `months_since_treatment`
      columns, ready for DiD analysis.
    - `did_panel_csv`: Path to did_panel DataFrame saved as csv
    """

    def __init__(self, min_pre_periods: int = 6, k_neighbors: int = 3) -> None:
        """Initialize the treatment indicator processor."""
        super().__init__(
            "treatment_indicator",
            "Create treatment indicators for difference-in-differences analysis",
        )
        self.min_pre_periods = min_pre_periods
        self.k_neighbors = k_neighbors


    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create treatment indicators and relative time variables."""
        # Get data from context
        did_panel = context["did_panel"]

        panel = did_panel.copy()

        panel["month_numeric"] = ((panel["month"] - panel["month"].min()).dt.total_seconds() / (30 * 24 * 3600))
        
        min_event_time = (
            panel.groupby("tract_geoid")["months_since_treatment"]
            .min()
        )

        valid_tracts = min_event_time[
            (min_event_time <= self.min_pre_periods * -1) |
            (min_event_time.isna())
        ].index

        panel_filtered = panel[panel["tract_geoid"].isin(valid_tracts)]

        pre_trend_slopes = panel.groupby("tract_geoid")[["ever_treated"]].min()

        def get_tract_slope(group: pd.DataFrame) -> float:
            pre = group[group["months_since_treatment"] < 0]
            return linregress(pre["months_numeric"], pre["rental_price"]).slope

        slopes = panel_filtered.groupby("tract_geoid").apply(get_tract_slope)

        pre_trend_slopes["pre_trend_slope"] = slopes

        treated_trends = pre_trend_slopes[pre_trend_slopes["ever_treated"] == 1].copy()
        control_trends = pre_trend_slopes[pre_trend_slopes["ever_treated"] == 0].copy()

        k = min(self.k_neighbors, len(control_trends))

        # If there are no controls, produce an empty match df (avoid crashing downstream)
        if k == 0:
            matches = pd.DataFrame(columns=["treated_tract", "control_tract", "distance"])
        else:
            nn = NearestNeighbors(n_neighbors=k, metric="euclidean")
            nn.fit(control_trends[["pre_trend_slope"]].values)  # 2D input

            treated_ids = treated_trends.index.to_numpy()
            treated_slopes = treated_trends["pre_trend_slope"].to_numpy()

            # kneighbors on all treated at once (faster than looping)
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

            # Collect all unique matched tract IDs
            matched_tracts = pd.unique(
                matches[["treated_tract", "control_tract"]].to_numpy().ravel()
            )

            # Filter original DiD panel
            did_panel_matched = did_panel[
                did_panel["tract_geoid"].isin(matched_tracts)
            ].copy()

            return {"did_panel_matched": did_panel_matched}


            

        


