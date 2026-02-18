"""Creates a treatment indicator with thresholds for the census tracts"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentThresholdProcessor(DataProcessor):
    """Create a treatment indicator using a share-of-units threshold.

    A tract is treated in a month only if it has a first prohibition date
    on or before that month AND (units restricted / total occupied units) >= threshold.
    """

    def __init__(self) -> None:
        """Initialize the processor."""
        super().__init__(
            "did_panel_data",
            "Create a treatment indicator for the census tracts (threshold-based)",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create a treatment indicator with thresholds for the census tracts."""
        tract_panel_data = context["tract_panel_data"]
        census_data = context.get("census_data")
        str_tract_data = context.get("str_tract_data")

        # Merge str_tract_data with tract_panel_data, merge on month and tract_geoid
        tract_panel_data["month"] = (
            pd.to_datetime(tract_panel_data["month"])
            .dt.to_period("M")
            .dt.to_timestamp()
        )
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

        merged["treated_units_in_month"] = merged["treated_units_in_month"].fillna(0)

        # Merge census total occupied housing units (denominator)
        if census_data is not None and "total_occupied_units" in census_data.columns:
            census_tract = census_data[["tract_id", "total_occupied_units"]].copy()
            census_tract = census_tract.rename(
                columns={"total_occupied_units": "total_occupied_units"}
            )
            merged = merged.merge(
                census_tract,
                left_on="tract_geoid",
                right_on="tract_id",
                how="left",
            )
            merged = merged.drop(columns=["tract_id"], errors="ignore")
        else:
            merged["total_occupied_units"] = pd.NA
            logger.warning(
                "No census_data or total_occupied_units; threshold uses units only."
            )

        merged = merged.sort_values(["tract_geoid", "month"])
        merged["cumulative_treated_units"] = merged.groupby("tract_geoid")[
            "treated_units_in_month"
        ].cumsum()

        # Share restricted = units prohibited / total_occupied (0 where no data or denominator 0)
        prohibited_units = merged["cumulative_treated_units"].fillna(0)
        total_occupied_units = merged["total_occupied_units"].fillna(0)
        total_occupied_units = total_occupied_units.replace(0, pd.NA)
        merged["pct_units_restricted"] = (
            (prohibited_units / total_occupied_units).fillna(0).astype(float)
        )

        # Treated = (month >= first prohibition) AND (pct_units_restricted >= threshold)
        THRESHOLD = 0.05

        # Find the first month that the tract is considered treated with the threshold
        treatment_start_month = (
            merged[merged["pct_units_restricted"] >= THRESHOLD]
            .groupby("tract_geoid")["month"]
            .min()
            .reset_index()
            .rename(columns={"month": "treatment_start_month"})
        )
        merged = merged.merge(
            treatment_start_month,
            on=["tract_geoid"],
            how="left",
        )

        # Treated = 1 if month >= treatment_start_month; else 0
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

        logger.info(
            "Created DiD panel with threshold=%.2f, %d observations",
            THRESHOLD,
            len(merged),
        )
        logger.info("Sample data:\n%s", merged.head(10))

        never_treated = merged[merged["treatment_start_month"].isna()]
        never_treated_check = (never_treated["treated"] == 0).all()
        logger.info(
            "Validation: never-treated tracts have treated=0: %s", never_treated_check
        )

        treatment_counts = merged.groupby("treated")["tract_geoid"].nunique()
        logger.info("Tracts by treatment status:\n%s", treatment_counts)

        output_path = "/project/output/did_panel_data.csv"
        merged.to_csv(output_path, index=False)
        logger.info("Saved DiD panel data to: %s", output_path)

        return {"did_panel_data": merged}
