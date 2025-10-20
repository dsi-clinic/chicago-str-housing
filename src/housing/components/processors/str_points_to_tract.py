"""STR point data to census tract aggregation processor."""

import logging
from typing import Any

from housing.components.processors.points_to_tract import PointsToTractProcessor

logger = logging.getLogger(__name__)


class STRToTractProcessor(PointsToTractProcessor):
    """Convenience class for STR listings → tracts aggregation."""

    def __init__(
        self,
        input_key: str = "str_data",
        output_key: str = "str_tract_data",
        id_column: str = "id",
    ) -> None:
        """Initialize STR to tract processor.

        Args:
            input_key: Context key for STR point data
            output_key: Context key for output tract data
            id_column: Column with listing IDs
        """
        super().__init__(
            input_key=input_key,
            output_key=output_key,
            id_column=id_column,
            aggregate_columns={},
            calculate_density=True,
        )

        def execute(self, context: dict[str, Any]) -> dict[str, Any]:
            """Ensure tract_boundaries exist in context before running."""
            if "tract_boundaries" not in context:
                raise KeyError(
                    "STRToTractProcessor requires 'tract_boundaries' in context. "
                    "Make sure you registered TractBoundariesLoader first."
                )

            # Now call the parent method (does the spatial join and aggregation)
            return super().execute(context)
