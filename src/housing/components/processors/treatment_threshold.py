"""Creates a treatment indicator with thresholds for the census tracts.

A tract is treated in a month only if it has a first prohibition date
on or before that month AND (units restricted / total occupied units) >= threshold.

When threshold logic yields only one group, falls back to TreatmentIndicator logic
(first-prohibition-date treatment) so downstream components receive both groups.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentThresholdProcessor(DataProcessor):
    """Create a treatment indicator using a share-of-units threshold.

    A tract is treated in a month only if it has a first prohibition date
    on or before that month AND (units restricted / total occupied units) >= threshold.

    If threshold logic yields only one group (all treated or all never-treated),
    falls back to first-prohibition-date treatment for compatibility with downstream.
    """

    def __init__(
        self,
        output_dir: str | None = None,
        percentile: float = 0.50,
    ) -> None:
        """Initialize the processor."

        Args:
            output_dir: Optional output directory for CSVs.
            percentile: Percentile for yearly threshold (0–1). Default 0.25 = 25th percentile.
        """
        super().__init__(
            "treatment_threshold",
            "Create a treatment indicator for the census tracts (threshold-based)",
        )
        self.output_dir = output_dir or "/project/output"
        self.percentile = percentile

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create a treatment indicator with thresholds for the census tracts."""
        tract_panel_data = context["tract_panel_data"].copy()
        census_data = context.get("census_data")
        str_tract_data = context.get("str_tract_data")

        if str_tract_data is None:
            raise ValueError(
                "TreatmentThresholdProcessor requires str_tract_data. "
                "Add PointsToTractProcessor (with number_of_units) before this component."
            )

        tract_panel_data["month"] = (
            pd.to_datetime(tract_panel_data["month"])
            .dt.to_period("M")
            .dt.to_timestamp()
        )
        str_tract_data = str_tract_data.copy()
        str_tract_data["prohibition_month"] = (
            pd.to_datetime(str_tract_data["prohibition_date"])
            .dt.to_period("M")
            .dt.to_timestamp()
        )

        prohibited_units_by_month = str_tract_data[
            ["tract_geoid", "prohibition_month", "number_of_units"]
        ].rename(
            columns={
                "prohibition_month": "month",
                "number_of_units": "treated_units_in_month",
            }
        )

        merged = tract_panel_data.merge(
            prohibited_units_by_month,
            on=["tract_geoid", "month"],
            how="left",
        )

        merged["treated_units_in_month"] = pd.to_numeric(
            merged["treated_units_in_month"], errors="coerce"
        ).fillna(0)

        census_tract = census_data[["tract_id", "total_occupied_units"]].copy()
        merged = merged.merge(
            census_tract,
            left_on="tract_geoid",
            right_on="tract_id",
            how="left",
        )
        merged = merged.drop(columns=["tract_id"], errors="ignore")

        merged = merged.sort_values(["tract_geoid", "month"])
        merged["cumulative_treated_units"] = merged.groupby("tract_geoid")[
            "treated_units_in_month"
        ].cumsum()

        prohibited_units = pd.to_numeric(
            merged["cumulative_treated_units"], errors="coerce"
        ).fillna(0)
        total_occupied_units = pd.to_numeric(
            merged["total_occupied_units"], errors="coerce"
        ).replace(0, np.nan)
        merged["pct_units_restricted"] = (
            prohibited_units / total_occupied_units
        ).fillna(0)

        merged["year"] = merged["month"].dt.year
        active_prohibitions = merged[merged["pct_units_restricted"] > 0].copy()

        thresholds_by_year = (
            active_prohibitions.groupby("year")["pct_units_restricted"]
            .quantile(self.percentile)
            .reset_index()
            .rename(columns={"pct_units_restricted": "threshold"})
        )

        merged = merged.merge(thresholds_by_year, on="year", how="left")
        merged["threshold"] = merged["threshold"].fillna(1.0)

        above_threshold = merged["pct_units_restricted"] >= merged["threshold"]
        treatment_start_month = (
            merged.loc[above_threshold]
            .groupby("tract_geoid")["month"]
            .min()
            .reset_index()
            .rename(columns={"month": "treatment_start_month"})
        )
        merged = merged.merge(treatment_start_month, on="tract_geoid", how="left")

        merged["treated"] = (
            merged["treatment_start_month"].notna()
            & (
                merged["month"].dt.to_period("M")
                >= merged["treatment_start_month"].dt.to_period("M")
            )
        ).astype(int)

        merged["months_since_treatment"] = (
            merged["month"].dt.year - merged["treatment_start_month"].dt.year
        ) * 12 + (merged["month"].dt.month - merged["treatment_start_month"].dt.month)
        merged["first_prohibition_date"] = merged["treatment_start_month"]

        logger.info("Created DiD panel with threshold-based treatment indicator")

        treatment_counts = merged.groupby("treated")["tract_geoid"].nunique()
        logger.info("Tracts by treatment status:\n%s", treatment_counts)

        output_path = Path(self.output_dir) / "did_panel_data.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(output_path, index=False)
        logger.info("Saved DiD panel data to: %s", output_path)

        return {"did_panel": merged, "did_panel_csv": str(output_path)}
