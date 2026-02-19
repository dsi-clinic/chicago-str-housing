
import logging
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TimeSeriesRentalLoader(DataLoader):
    """Load monthly rental price panel data.

    Loads data from Zillow Observed Rent Index (ZORI) dataset and
    transforms it from wide format to long format (panel data).
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the time series rental loader.

        Args:
            file_path: Optional path to rental data file
        """
        super().__init__(
            "rental_panel_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load and reshape monthly rental price data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and reshape rental data."""
        logger.info("Loading rental time series from: %s", self.file_path)

        try:
            # Only load necessary columns to save memory?
            # For now load all, assuming file fits in memory
            wide_df = pd.read_csv(self.file_path)
            logger.info("Raw data shape: %s", wide_df.shape)
        except Exception as e:
            logger.error("Failed to load rental data: %s", e)
            raise

        # 1. Identify date columns
        date_cols = [col for col in wide_df.columns if col.startswith("20")]
        logger.info("Found %d date columns", len(date_cols))

        if not date_cols:
            raise ValueError("No date columns (starting with '20') found in rental data")

        # 2. Reshape from wide to long
        # Ensure RegionName exists (standard Zillow format)
        id_col = "RegionName"
        if id_col not in wide_df.columns:
            # Try to find zip code column
            for col in ["zip_code", "ZipCode", "RegionID"]:
                if col in wide_df.columns:
                    id_col = col
                    break
        
        if id_col not in wide_df.columns:
             raise ValueError("Could not identify zip code column (RegionName)")

        long_df = wide_df.melt(
            id_vars=[id_col],
            value_vars=date_cols,
            var_name="month",
            value_name="rental_price",
        )

        # 3. Clean and validate
        long_df = long_df.rename(columns={id_col: "zip_code"})
        
        # Pad zip codes to 5 digits
        long_df["zip_code"] = long_df["zip_code"].astype(str).str.zfill(5)
        
        # Convert month to datetime
        long_df["month"] = pd.to_datetime(long_df["month"])
        
        # 4. Impute missing values
        # Sort for proper interpolation
        long_df = long_df.sort_values(["zip_code", "month"])
        
        # Interpolate within each zip code
        logger.info("Imputing missing rental prices via linear interpolation...")
        long_df["rental_price"] = (
            long_df.groupby("zip_code")["rental_price"]
            .transform(lambda x: x.interpolate(method="linear").ffill().bfill())
        )
        
        # Final cleanup
        long_df = long_df.dropna(subset=["rental_price"]).reset_index(drop=True)
        
        logger.info("Loaded panel data with %d observations", len(long_df))
        logger.info("Date range: %s to %s", long_df["month"].min(), long_df["month"].max())
        logger.info("Unique ZIP codes: %d", long_df["zip_code"].nunique())

        return {"rental_panel_data": long_df}
