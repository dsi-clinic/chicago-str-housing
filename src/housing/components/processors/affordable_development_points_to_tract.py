"""Class that aggregates tract-level data for the affordable housing dataset through a spatial join"""

import logging

from housing import PointsToTractProcessor

logger = logging.getLogger(__name__)


class AirbnbToTractProcessor(PointsToTractProcessor):
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
            input_key: Context key for Airbnb point data
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
        )
