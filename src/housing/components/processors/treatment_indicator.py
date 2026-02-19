
import logging
from typing import Any

import geopandas as gpd
import pandas as pd
import numpy as np

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class TreatmentIndicatorProcessor(DataProcessor):
    """Adds treatment indicators for Difference-in-Differences analysis.
    
    Creates 'treated' (binary) and 'months_since_treatment' (int) variables
    based on STR prohibition dates.
    """

    def __init__(self) -> None:
        """Initialize the processor."""
        super().__init__(
            "did_panel_data",
            "Add treatment indicators for DiD analysis"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the processing."""
        logger.info("Adding treatment indicators to panel data...")

        panel_df = context.get("tract_rental_panel")
        if panel_df is None:
            raise ValueError("tract_rental_panel not found in context")

        # 1. Get prohibition dates
        try:
            tract_dates = self._get_prohibition_dates(context)
        except Exception as e:
            logger.error(f"Failed to determine prohibition dates: {e}")
            # If we fail, we might return panel without treatment info?
            # Or raise error. DiD requires it.
            raise
            
        # 2. Merge panel with treatment dates
        merged = panel_df.merge(
            tract_dates[["tract_geoid", "first_prohibition_date"]],
            on="tract_geoid",
            how="left"
        )
        
        # 3. Create treated indicator
        # treated = 1 if month >= first_prohibition_date
        # Handle NaT for never-treated using fillna(False) implicitly via astype(int)?
        # Comparison with NaT usually False.
        
        merged["treated"] = (
            merged["month"] >= merged["first_prohibition_date"]
        ).astype(int)
        
        # 4. Relative time: months_since_treatment
        # (Year diff * 12) + Month diff
        
        # Vectorized calculation
        # We need first_prohibition_date to be datetime
        if not pd.api.types.is_datetime64_any_dtype(merged["first_prohibition_date"]):
             merged["first_prohibition_date"] = pd.to_datetime(merged["first_prohibition_date"])
             
        # Create mask for treated units
        is_treated = merged["first_prohibition_date"].notna()
        
        merged["months_since_treatment"] = np.nan
        
        if is_treated.any():
            treated_subset = merged.loc[is_treated]
            months_diff = (
                (treated_subset["month"].dt.year - treated_subset["first_prohibition_date"].dt.year) * 12 +
                (treated_subset["month"].dt.month - treated_subset["first_prohibition_date"].dt.month)
            )
            merged.loc[is_treated, "months_since_treatment"] = months_diff

        # Validation
        treated_count = merged["treated"].sum()
        logger.info(f"Created DiD panel with {len(merged)} observations")
        logger.info(f"Treatment status: {treated_count} treated tract-months")
        
        return {"did_panel": merged}

    def _get_prohibition_dates(self, context: dict[str, Any]) -> pd.DataFrame:
        """Retrieve or calculate tract prohibition dates."""
        
        # Try finding pre-calculated dates
        tract_dates = context.get("tract_prohibition_dates")
        if tract_dates is not None:
            return tract_dates
            
        logger.info("calculating tract prohibition dates from raw data...")
        
        # Calculate from raw data
        str_data = context.get("str_prohibition_data")
        tract_boundaries = context.get("tract_boundaries")
        
        if str_data is None:
            raise ValueError("Missing str_prohibition_data to calculate dates")
        if tract_boundaries is None:
             # Try generic boundaries if available? No, need specific key
             raise ValueError("Missing tract_boundaries to calculate dates")
             
        # Spatial join to link buildings to tracts
        if not isinstance(str_data, gpd.GeoDataFrame):
             raise ValueError("str_prohibition_data must be a GeoDataFrame")
             
        # Ensure CRS match
        if str_data.crs != tract_boundaries.crs:
            str_data = str_data.to_crs(tract_boundaries.crs)
            
        joined = gpd.sjoin(str_data, tract_boundaries, how="inner", predicate="within")
        
        # Check column for date
        date_col = "prohibition_date"
        if date_col not in joined.columns:
            # Fallback
            if "signed_date" in joined.columns:
                date_col = "signed_date"
            elif "recorded_date" in joined.columns:
                date_col = "recorded_date"
            else:
                raise ValueError("No valid date column found in prohibition data")
                
        # Group by tract and find earliest date
        tract_dates = (
            joined.groupby("tract_geoid")[date_col]
            .min()
            .reset_index()
            .rename(columns={date_col: "first_prohibition_date"})
        )
        
        logger.info(f"Calculated first prohibition dates for {len(tract_dates)} tracts")
        return tract_dates
