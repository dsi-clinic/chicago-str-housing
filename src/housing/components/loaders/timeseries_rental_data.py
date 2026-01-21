"""Time series rental data loader for ZORI dataset.

This module loads rental price time series data from the Zillow Observed Rent Index (ZORI) dataset,
reshaping it from wide format (one column per month) to long format (panel data).
"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TimeSeriesRentalLoader(DataLoader):
    """Load rental price time series data from ZORI dataset.

    This loader:
    1. Loads CSV data with geographic identifiers (zip codes)
    2. Identifies date columns (columns starting with "20" representing years)
    3. Reshapes data from wide format to long format (panel data)
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the time series rental data loader.

        Args:
            file_path: Optional path to rental data file
        """
        super().__init__(
            "timeseries_rental_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load rental price time series data and reshape to panel format",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load CSV, identify date columns, and reshape to long format.

        Returns:
            Dictionary with 'timeseries_rental_data' key containing panel DataFrame
            with columns: zip_code, month, rental_price
        """
        # Step 1: Load CSV
        logger.info("Loading time series rental data from: %s", self.file_path)

        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Time series rental data file not found: {self.file_path}"
            )

        rental_df = pd.read_csv(self.file_path)
        logger.info(
            "Loaded CSV with %d rows and %d columns",
            len(rental_df),
            len(rental_df.columns),
        )

        # Clean and prepare the data - rename RegionName to zip_code
        if "RegionName" in rental_df.columns:
            rental_df = rental_df.rename(columns={"RegionName": "zip_code"})

        if "zip_code" in rental_df.columns:
            rental_df["zip_code"] = rental_df["zip_code"].astype(str).str.zfill(5)

        # Step 2: Identify date columns
        date_columns = [col for col in rental_df.columns if col.startswith("20")]
        logger.info("Identified %d date columns", len(date_columns))

        if not date_columns:
            date_cols = []
            for col in rental_df.columns:
                try:
                    pd.to_datetime(col)
                    date_cols.append(col)
                except (ValueError, TypeError):
                    # Column is not a valid date format, skip it
                    pass
            date_columns = date_cols
            if date_columns:
                logger.info(
                    "Found %d date columns via alternative detection", len(date_columns)
                )

        # Step 3: Reshape to long format using pd.melt()

        logger.info("Reshaping data from wide to long format")
        logger.info("ID variables: %s", "zip_code")
        logger.info("Date columns (first 5): %s", date_columns[:5])

        # Melt the DataFrame: wide format -> long format
        long_df = rental_df.melt(
            id_vars="zip_code",
            value_vars=date_columns,
            var_name="month",
            value_name="rental_price",
        )

        # Sort by zip_code and month for easier inspection
        long_df = long_df.sort_values(by=["zip_code", "month"]).reset_index(drop=True)

        # Interpolate missing values within each ZIP code
        long_df["rental_price"] = long_df.groupby("zip_code")["rental_price"].transform(
            lambda x: x.interpolate(method="linear")
        )

        # For any remaining NaNs at the edges, forward/backward fill
        long_df["rental_price"] = long_df.groupby("zip_code")["rental_price"].transform(
            lambda x: x.ffill().bfill()
        )

        # Convert month to datetime
        long_df["month"] = pd.to_datetime(long_df["month"], format="%Y-%m-%d")

        logger.info("Reshaped to panel format: %d rows", len(long_df))
        logger.info("Unique zip codes: %d", long_df["zip_code"].nunique())
        logger.info(
            "Date range: %s to %s", long_df["month"].min(), long_df["month"].max()
        )
        logger.info(
            "Rental price range: $%.0f - $%.0f",
            long_df["rental_price"].min(),
            long_df["rental_price"].max(),
        )

        return {"timeseries_rental_data": long_df}
