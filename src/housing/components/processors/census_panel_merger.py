"""Merge census data into the DiD panel for triple-difference analysis.

Census provides cross-sectional tract-level variables (e.g. median_income, pct_rented)
that define the third dimension in a DDD design.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class CensusPanelMerger(DataProcessor):
    """Merge census data into the DiD panel so each tract-month has census variables."""

    def __init__(
        self,
        census_tract_id_column: str = "tract_id",
        panel_tract_column: str = "tract_geoid",
        census_columns: list[str] | None = None,
    ) -> None:
        """Initialize the census panel merger.

        Args:
            census_tract_id_column: Census DataFrame column for tract ID (FIPS).
            panel_tract_column: Panel DataFrame column for tract ID.
            census_columns: Census columns to merge (None = all numeric/identifier).
        """
        super().__init__(
            "census_panel_merger",
            "Merge census data into DiD panel for triple-difference analysis",
        )
        self.census_tract_id_column = census_tract_id_column
        self.panel_tract_column = panel_tract_column
        self.census_columns = census_columns
        self.required_data = ["did_panel", "census_data"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Merge census into did_panel; output ddd_panel with census columns."""
        did_panel = context["did_panel"].copy()
        census_data = context["census_data"].copy()

        # Align tract IDs: census uses tract_id, panel uses tract_geoid (same FIPS)
        census_data = census_data.rename(
            columns={self.census_tract_id_column: self.panel_tract_column}
        )

        cols_to_merge = self.census_columns
        if cols_to_merge is None:
            # Default: key census variables (exclude raw FIPS/name if present)
            want = [
                "median_income",
                "total_population",
                "median_house_value",
                "median_age",
                "pct_bachelor",
                "pct_rented",
            ]
            cols_to_merge = [
                c for c in want
                if c in census_data.columns
            ]
        else:
            cols_to_merge = [
                c for c in cols_to_merge
                if c in census_data.columns
            ]

        merge_cols = [self.panel_tract_column] + cols_to_merge
        census_sub = census_data[merge_cols].drop_duplicates(
            subset=[self.panel_tract_column], keep="first"
        )

        ddd_panel = did_panel.merge(
            census_sub,
            on=self.panel_tract_column,
            how="left",
        )

        n_matched = ddd_panel[cols_to_merge[0]].notna().sum() if cols_to_merge else 0
        logger.info(
            "Merged census into panel: %d rows, %d with census data",
            len(ddd_panel),
            n_matched,
        )

        return {"ddd_panel": ddd_panel}
