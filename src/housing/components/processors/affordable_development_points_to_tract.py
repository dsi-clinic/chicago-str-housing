"""Class that aggregates tract-level data for the affordable housing dataset through a spatial join"""

import logging
from typing import Any

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class AffordableTractDensityProcessor(DataProcessor):
    """Adds Unit Density Column to Affordable Developments Tract-Level Data"""
    def __init__(self) -> None:
        """Initialize the affordable developments unit density processor."""
        super().__init__(
            "affordable_development_tract_data", "Adds unit density column to affordable tract data"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Add unit density column to affordable tract data."""

        tract_data = context["affordable_developments_tract_data"]

        tract_data["unit_density"] = (tract_data["units_sum"] / tract_data["area_km2"])
        
        logger.info(
                    "Density range: %.2f - %.2f units/km²",
                    tract_data["unit_density"].min(),
                    tract_data["unit_density"].max(),
                )
        
        logger.info("Filling NaN Values with 0 ...")

        tract_data["unit_density"] = tract_data["unit_density"].fillna(0)
        
        return {"affordable_development_tract_data": tract_data}
