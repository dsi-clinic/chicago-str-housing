"""Tract prohibition dates processor for DiD analysis.

This module aggregates building-level STR prohibition data to tract-level
treatment dates, identifying when each census tract first received an
STR prohibition (treatment).
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TractProhibitionDatesProcessor(DataProcessor):
    """Aggregate STR prohibition data to tract-level treatment dates.

    This processor:
    1. Performs spatial join to assign each building to a census tract
    2. Finds the first prohibition date for each tract
    3. Counts the number of buildings with prohibitions per tract
    4. Returns tract-level treatment dates for DiD analysis

    Tracts not in the output are considered "never treated" (control group).
    """

    def __init__(
        self,
        output_dir: str | None = None,
        output_path: str | None = None,
    ) -> None:
        """Initialize the tract prohibition dates processor.

        Args:
            output_dir: Directory for ``tract_prohibition_dates.csv`` (default /project/output).
            output_path: If set, write CSV exactly to this path (overrides output_dir).
        """
        super().__init__(
            "tract_prohibition_dates",
            "Aggregate building-level STR prohibitions to tract-level treatment dates",
        )
        self.required_data = ["str_prohibition_data", "tract_boundaries"]
        self.output_dir = output_dir
        self.output_path = output_path

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Aggregate STR prohibition data to tract level.

        Required context keys:
            - str_prohibition_data: GeoDataFrame with building-level prohibition data
            - tract_boundaries: GeoDataFrame with census tract geometries

        Returns:
            Dictionary with 'tract_prohibition_dates' containing a DataFrame with columns:
            - tract_geoid: Census tract GEOID
            - first_prohibition_date: Date of first STR prohibition in the tract
            - building_count: Number of buildings with prohibitions in the tract
        """
        str_data = context["str_prohibition_data"].copy()
        tract_boundaries = context["tract_boundaries"]

        logger.info(
            "Aggregating STR prohibition data to tract-level treatment dates..."
        )
        logger.info("  Input STR prohibition buildings: %d", len(str_data))
        logger.info("  Census tracts available: %d", len(tract_boundaries))

        if str_data.crs != tract_boundaries.crs:
            str_data = str_data.to_crs(tract_boundaries.crs)

        str_with_tract = gpd.sjoin(
            str_data,
            tract_boundaries[["tract_geoid", "geometry"]],
            how="left",
            predicate="within",
        )

        unmatched = str_with_tract["tract_geoid"].isna().sum()
        if unmatched > 0:
            logger.warning(
                "  %d buildings not within any tract boundary (dropped)",
                unmatched,
            )
            str_with_tract = str_with_tract.dropna(subset=["tract_geoid"])

        logger.info("  Buildings matched to tracts: %d", len(str_with_tract))

        if "prohibition_date" in str_with_tract.columns:
            date_col = "prohibition_date"
        elif "signed_date" in str_with_tract.columns:
            date_col = "signed_date"
        elif "recorded_date" in str_with_tract.columns:
            date_col = "recorded_date"
        else:
            raise ValueError(
                "No date column found in STR prohibition data. "
                "Expected 'prohibition_date', 'signed_date', or 'recorded_date'."
            )

        logger.info("  Using date column: %s", date_col)

        str_with_tract[date_col] = pd.to_datetime(str_with_tract[date_col])

        id_col = (
            "application_id"
            if "application_id" in str_with_tract.columns
            else str_with_tract.columns[0]
        )

        tract_dates = (
            str_with_tract.groupby("tract_geoid")
            .agg(
                {
                    date_col: "min",
                    id_col: "count",
                }
            )
            .reset_index()
        )

        tract_dates = tract_dates.rename(
            columns={
                date_col: "first_prohibition_date",
                id_col: "building_count",
            }
        )

        tract_dates = tract_dates.sort_values("first_prohibition_date").reset_index(
            drop=True
        )

        n_treated_tracts = len(tract_dates)
        n_total_tracts = len(tract_boundaries)
        n_never_treated = n_total_tracts - n_treated_tracts

        logger.info("Tract prohibition dates created successfully:")
        logger.info("  Tracts with prohibitions (treated): %d", n_treated_tracts)
        logger.info("  Tracts without prohibitions (control): %d", n_never_treated)
        logger.info(
            "  Treatment rate: %.1f%%",
            100 * n_treated_tracts / n_total_tracts,
        )
        logger.info(
            "  Date range: %s to %s",
            tract_dates["first_prohibition_date"].min().strftime("%Y-%m-%d"),
            tract_dates["first_prohibition_date"].max().strftime("%Y-%m-%d"),
        )
        logger.info(
            "  Buildings per treated tract: min=%d, median=%.0f, max=%d",
            tract_dates["building_count"].min(),
            tract_dates["building_count"].median(),
            tract_dates["building_count"].max(),
        )

        if self.output_path:
            out_file = Path(self.output_path)
        else:
            base = Path(self.output_dir or "/project/output")
            out_file = base / "tract_prohibition_dates.csv"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        tract_dates.to_csv(out_file, index=False)
        logger.info("  Saved to: %s", out_file)

        return {"tract_prohibition_dates": tract_dates}
