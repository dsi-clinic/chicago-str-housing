"""Creates a treatment indicator for the census tracts"""

import logging
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentIndicatorProcessor(DataProcessor):
    """Creates a treatment indicator for the census tracts.
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
        
        # Create treated indicator where treated = 1 if month >= first_prohibition_date, else 0
        # Tracts that are never treated are assigned a 0.
        merged["treated"] = (
            (merged["first_prohibition_date"].notna()) & 
            (merged["month"] >= merged["first_prohibition_date"])
        ).astype(int)
        
        merged["months_since_treatment"] = (
            (merged["month"].dt.year - merged["first_prohibition_date"].dt.year) * 12 +
            (merged["month"].dt.month - merged["first_prohibition_date"].dt.month)
        )
        
        logger.info("Created DiD panel with %d observations", len(merged))
        logger.info("Sample data:\n%s", merged.head(10))
        
        # Count treated vs control
        logger.info("\n3. Treatment Distribution:")
        treatment_counts = merged.groupby("treated")["tract_geoid"].nunique()
        logger.info("Tracts by treatment status:\n%s", treatment_counts)
        
        # Save DiD panel data
        output_path = "/project/output/did_panel_data.csv"
        merged.to_csv(output_path, index=False)
        logger.info("Saved DiD panel data to: %s", output_path)
    
        return {"did_panel_data": merged}