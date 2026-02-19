
import logging
from typing import Any

import pandas as pd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TimeSeriesZipToTractProcessor(DataProcessor):
    """Convert ZIP-level rental panel to tract-level panel using crosswalk.
    
    Uses area-weighted interpolation to transform data from ZIP codes to Census Tracts.
    """

    def __init__(self) -> None:
        """Initialize the processor."""
        super().__init__(
            "zip_to_tract_panel",
            "Convert ZIP rental panel to Tract panel"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the conversion."""
        logger.info("Converting ZIP panel to Tract panel...")

        zip_panel = context.get("rental_panel_data")
        crosswalk = context.get("zip_to_tract_crosswalk")

        if zip_panel is None:
            raise ValueError("rental_panel_data not found in context")
        if crosswalk is None:
            raise ValueError("zip_to_tract_crosswalk not found in context")

        # Ensure types match for merge
        # Zip inputs are strings from loader and crosswalk
        
        # 1. Merge panel data with crosswalk
        # This expands ZIP-month rows to Tract-ZIP-month rows
        merged = zip_panel.merge(crosswalk, on="zip_code", how="inner")
        
        if merged.empty:
            logger.warning("Merge of rental data and crosswalk resulted in empty dataframe!")
            return {"tract_rental_panel": pd.DataFrame()}
            
        # 2. Calculate weighted rental prices
        # weight = intersection_area (from ZipToTractProcessor)
        if "intersection_area" not in merged.columns:
             # Fallback if crosswalk columns differ
             logger.warning("intersection_area not found in crosswalk, looking for weight column")
             if "weight" in merged.columns:
                 merged["intersection_area"] = merged["weight"]
             else:
                 raise ValueError("Crosswalk missing intersection_area or weight column")

        merged["weighted_rent"] = merged["rental_price"] * merged["intersection_area"]

        # 3. Aggregate to tract level for each month
        tract_panel = (
            merged.groupby(["tract_geoid", "month"])
            .agg({
                "weighted_rent": "sum",
                "intersection_area": "sum"
            })
            .reset_index()
        )

        # 4. Normalize to get tract-level rental price
        # Avoid division by zero
        tract_panel = tract_panel[tract_panel["intersection_area"] > 0].copy()
        
        tract_panel["rental_price"] = (
            tract_panel["weighted_rent"] / tract_panel["intersection_area"]
        )

        # Clean up
        cols = ["tract_geoid", "month", "rental_price"]
        tract_panel = tract_panel[cols].sort_values(["tract_geoid", "month"])
        
        logger.info("Generated tract panel with %d observations", len(tract_panel))
        logger.info("Unique tracts: %d", tract_panel["tract_geoid"].nunique())

        return {"tract_rental_panel": tract_panel}
