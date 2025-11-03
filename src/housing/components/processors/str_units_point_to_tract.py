import logging
from typing import Any

import numpy as np
import pandas as pd

from housing.components.processors.points_to_tract import PointsToTractProcessor

logger = logging.getLogger(__name__)


class STRUnitsToTractProcessor(PointsToTractProcessor):
    """Aggregate STR units data to census tracts, summing number of units."""

    def __init__(
        self,
        input_key: str = "str_data",
        output_key: str = "str_units_tract_data",
        id_column: str = "submission_id",
        number_of_units_column: str = "number_of_units",
    ) -> None:
        super().__init__(
            input_key=input_key,
            output_key=output_key,
            id_column=None,
            aggregate_columns={number_of_units_column: ["sum"]},
            calculate_density=True,
            data_source_name="str_units",
        )
        self.number_of_units_column = number_of_units_column

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info(f"Context keys available: {list(context.keys())}")

        if "tract_boundaries" not in context:
            raise KeyError(
                "STRUnitsToTractProcessor requires 'tract_boundaries' in context. "
                "Make sure you registered TractBoundariesLoader first."
            )

        # Clean input
        str_data = context[self.input_key]
        if self.number_of_units_column in str_data.columns:
            # Convert to numeric, make NaN values to 0
            str_data[self.number_of_units_column] = pd.to_numeric(
                str_data[self.number_of_units_column], errors="coerce"
            ).fillna(0)
            # Remove
            str_data.loc[
                str_data[self.number_of_units_column] > 1e4, self.number_of_units_column
            ] = 0
            logger.info(
                "Cleaned 'number_of_units' in STR units data: min=%.2f, max=%.2f",
                str_data[self.number_of_units_column].min(),
                str_data[self.number_of_units_column].max(),
            )
        else:
            logger.warning(
                f"Column {self.number_of_units_column} not found in input STR units data."
            )

        context[self.input_key] = str_data

        # Running parent processor
        result = super().execute(context)

        # Sanity Check
        tract_data = result[self.output_key]
        max_units = tract_data["number_of_units_sum"].max()
        min_units = tract_data["number_of_units_sum"].min()
        logger.info(
            "Post-aggregation unit totals: min=%.2f, max=%.2f", min_units, max_units
        )

        # Recomputing Density
        tract_data["unit_density"] = (
            tract_data["number_of_units_sum"] / tract_data["area_km2"]
        )
        tract_data["unit_density"] = (
            tract_data["unit_density"].replace([np.inf, -np.inf], np.nan).fillna(0)
        )

        tract_data["number_of_units_sum"] = tract_data["number_of_units_sum"].fillna(0)

        tract_data = tract_data.drop(
            columns=["str_units_count", "str_units_density"]
        ).rename(
            columns={
                "number_of_units_sum": "str_units_count",
                "unit_density": "str_units_density",
            }
        )

        result[self.output_key] = tract_data
        context[self.output_key] = tract_data

        return {self.output_key: tract_data}
