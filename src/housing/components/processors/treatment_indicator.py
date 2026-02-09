"""Creates a treatment indicator for the census tracts"""

import logging
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentIndicatorProcessor(DataProcessor):
    """Create a treatment indicator for census tracts

    Creates a treatment indicator for the census tracts.
    The treatment indicator is a binary variable that is 1 if the tract is treated and 0 otherwise.
    The treatment indicator is created by merging the census tracts with the STR prohibition data.
    """

    def __init__(self) -> None:
        """Initialize the treatment indicator processor."""
        super().__init__(
            "did_panel_data",
            "Create a treatment indicator for the census tracts",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create a treatment indicator for the census tracts."""
        # Get the data from context
        treatment_dates = context["tract_prohibition_dates"]
        tract_panel_data = context["tract_panel_data"]

        merged = tract_panel_data.merge(
            treatment_dates[["tract_geoid", "first_prohibition_date"]],
            on="tract_geoid",
            how="left",
        )

        # Create treated indicator where treated = 1 if month is after the first prohibition date, else 0
        # Tracts that are never treated are assigned a 0.
        merged["treated"] = (
            (merged["first_prohibition_date"].notna())
            & (merged["month"].dt.to_period("M") >= merged["first_prohibition_date"].dt.to_period("M"))
        ).astype(int)

        merged["months_since_treatment"] = (
            merged["month"].dt.year - merged["first_prohibition_date"].dt.year
        ) * 12 + (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)

        logger.info("Created DiD panel with %d observations", len(merged))
        logger.info("Sample data:\n%s", merged.head(10))

        # Validation check
        # Check never-treated tracts have treated=0 always
        never_treated = merged[merged["first_prohibition_date"].isna()]
        never_treated_check = (never_treated["treated"] == 0).all()
        logger.info(
            "Validation: never-treated tracts have treated=0: %s", never_treated_check
        )

        # Check treated tracts switch at the right time
        treated_tracts = merged[merged["first_prohibition_date"].notna()]
        for tract_id, group in treated_tracts.groupby("tract_geoid"):
            first_treated_month = group.loc[group["treated"] == 1, "month"].min()
            prohibition_date = group["first_prohibition_date"].iloc[0]
            if first_treated_month.to_period("M") != prohibition_date.to_period("M"):
                logger.warning("Treatment date mismatch for %s", tract_id)
            # Check before and after treatment using year-month comparison
            treatment_month = prohibition_date.to_period("M").to_timestamp()
            month_normalized = group["month"].dt.to_period("M").dt.to_timestamp()
            before_treatment = group[month_normalized < treatment_month]
            at_after_treatment = group[month_normalized >= treatment_month]
            # Before treatment: all should be 0
            if (
                len(before_treatment) > 0
                and not (before_treatment["treated"] == 0).all()
            ):
                logger.warning(f"{tract_id}: treated!=0 before treatment month")
            # At/after treatment: all should be 1
            if (
                len(at_after_treatment) > 0
                and not (at_after_treatment["treated"] == 1).all()
            ):
                logger.warning(f"{tract_id}: treated!=1 at/after treatment month")

        # Count treated vs control
        treatment_counts = merged.groupby("treated")["tract_geoid"].nunique()
        logger.info("Tracts by treatment status:\n%s", treatment_counts)

        # Save DiD panel data
        output_path = "/project/output/did_panel_data.csv"
        merged.to_csv(output_path, index=False)
        logger.info("Saved DiD panel data to: %s", output_path)

        return {"did_panel_data": merged}
