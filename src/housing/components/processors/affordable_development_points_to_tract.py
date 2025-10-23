"""Class that aggregates tract-level data for the affordable housing dataset through a spatial join"""

import logging
from typing import Any

from housing import PointsToTractProcessor

logger = logging.getLogger(__name__)


class AffordableToTractProcessor(PointsToTractProcessor):
    """Convenience class for affordable developments → tracts aggregation."""

    def __init__(
        self,
        input_key: str = "affordable_developments_data",
        output_key: str = "affordable_developments_tract_data",
        id_column: str = "property_name",
        unit_column: str = "units",
    ) -> None:
        """Initialize affordable development to tract processor.

        Args:
            input_key: Context key for affordable development point data
            output_key: Context key for output tract data
            id_column: Column with property IDs or names
            unit_column: Column with property affordable unit count
        """
        super().__init__(
            input_key=input_key,
            output_key=output_key,
            id_column=id_column,
            aggregate_columns={
                unit_column: ["sum", "mean"],
            },
            calculate_density=True,
            data_source_name="affordable_development",
        )
        self.unit_column = unit_column

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the base processor and add unit density calculation."""
        # Call parent execute method
        result = super().execute(context)

        # Get the tract data from the result
        tract_data = result[self.output_key]

        # Debug: Log what columns we actually have
        logger.info(
            "Available columns after base processing: %s", list(tract_data.columns)
        )

        # Calculate unit density if we have units_sum column
        if f"{self.unit_column}_sum" in tract_data.columns:
            tract_data["unit_density"] = (
                tract_data[f"{self.unit_column}_sum"] / tract_data["area_km2"]
            )
            tract_data["unit_density"] = tract_data["unit_density"].fillna(0)
            logger.info(
                "Calculated unit density range: %.2f - %.2f units/km²",
                tract_data["unit_density"].min(),
                tract_data["unit_density"].max(),
            )
        else:
            logger.warning(
                "Column %s not found in tract data", f"{self.unit_column}_sum"
            )

        return result
