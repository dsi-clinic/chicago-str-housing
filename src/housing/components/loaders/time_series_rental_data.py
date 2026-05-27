"""Time series rental data loader for DiD analysis.

This module loads rental price data from the Zillow Observed Rent Index (ZORI) dataset
and converts it from wide format (one column per month) to long/panel format
(one row per ZIP-month combination) suitable for Difference-in-Differences analysis.
"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TimeSeriesRentalLoader(DataLoader):
    """Load rental price data in panel format for DiD analysis.

    This loader:
    1. Loads the ZORI CSV file with monthly rental prices
    2. Converts from wide format (one column per month) to long format
    3. Handles missing values via linear interpolation
    4. Returns panel data: (zip_code, month, rental_price)
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the time series rental data loader.

        Args:
            file_path: Optional path to rental data file
        """
        super().__init__(
            "rental_panel_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load all monthly rental price data in panel format",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and reshape rental data to panel format.

        Returns:
            Dictionary with 'rental_panel_data' containing a DataFrame with columns:
            - zip_code: 5-digit ZIP code string
            - month: datetime of the observation
            - rental_price: rental price for that ZIP-month
        """
        logger.info("Loading rental data from: %s", self.file_path)

        # Load the CSV data
        rental_df = pd.read_csv(self.file_path)

        # Clean and prepare the data
        rental_df = rental_df.rename(columns={"RegionName": "zip_code"})
        rental_df["zip_code"] = rental_df["zip_code"].astype(str).str.zfill(5)

        # Identify date columns (columns starting with "20")
        date_cols = [col for col in rental_df.columns if col.startswith("20")]
        logger.info("Found %d monthly date columns", len(date_cols))

        if not date_cols:
            raise ValueError(
                "No date columns found in rental data (expected columns starting with '20')"
            )

        # Log date range
        sorted_dates = sorted(date_cols)
        logger.info("Date range: %s to %s", sorted_dates[0], sorted_dates[-1])

        # Reshape from wide to long format using melt
        long_df = rental_df.melt(
            id_vars=["zip_code"],
            value_vars=date_cols,
            var_name="month",
            value_name="rental_price",
        )

        # Convert month to datetime
        long_df["month"] = pd.to_datetime(long_df["month"])

        # Sort by zip_code and month for proper interpolation
        long_df = long_df.sort_values(["zip_code", "month"]).reset_index(drop=True)

        # Count missing values before imputation
        missing_before = long_df["rental_price"].isna().sum()
        total_obs = len(long_df)
        logger.info(
            "Missing values before imputation: %d (%.1f%%)",
            missing_before,
            100 * missing_before / total_obs,
        )

        # Impute missing values using linear interpolation within each ZIP code
        long_df["rental_price"] = long_df.groupby("zip_code")["rental_price"].transform(
            lambda x: x.interpolate(method="linear")
        )

        # For any remaining NaNs at the edges, forward/backward fill
        long_df["rental_price"] = long_df.groupby("zip_code")["rental_price"].transform(
            lambda x: x.ffill().bfill()
        )

        # Count missing values after imputation
        missing_after = long_df["rental_price"].isna().sum()
        if missing_after > 0:
            logger.warning(
                "Still have %d missing values after imputation (ZIPs with no data)",
                missing_after,
            )
            # Drop ZIPs with no data at all
            long_df = long_df.dropna(subset=["rental_price"])

        # Log summary statistics
        n_zips = long_df["zip_code"].nunique()
        n_months = long_df["month"].nunique()
        n_obs = len(long_df)

        logger.info("Panel data created successfully:")
        logger.info("  Unique ZIP codes: %d", n_zips)
        logger.info("  Unique months: %d", n_months)
        logger.info("  Total observations: %d", n_obs)
        logger.info(
            "  Rental price range: $%.0f - $%.0f",
            long_df["rental_price"].min(),
            long_df["rental_price"].max(),
        )
        logger.info(
            "  Mean rental price: $%.0f",
            long_df["rental_price"].mean(),
        )

        return {"rental_panel_data": long_df}
