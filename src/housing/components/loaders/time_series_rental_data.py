"""Rental data loader for ZORI dataset.

This module loads rental price data from the Zillow Observed Rent Index (ZORI) dataset,
which provides zip code level rental price estimates. This also formats this into a time series, long format.
"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TimeSeriesRentalLoader(DataLoader):
    """Load rental price data from ZORI dataset, reshaped into long format.

    This demonstrates loading CSV data with geographic identifiers (zip codes).
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Load rental data.

        Args:
            file_path: Optional path to rental data file
        """
        super().__init__(
            "rental_panel_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load rental price data from ZORI dataset",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean rental data (put into time series format)."""
        logger.info("Loading rental data from: %s", self.file_path)

        # Get Chicago zip boundaries from context
        zip_boundaries = context["zip_boundaries"]
        chicago_zip_codes = set(zip_boundaries["zip_code"].unique())
        logger.info("Filtering to %d Chicago zip codes", len(chicago_zip_codes))

        # Load the CSV data
        rental_df = pd.read_csv(self.file_path)

        # Clean and prepare the data
        rental_df = rental_df.rename(columns={"RegionName": "zip_code"})
        rental_df["zip_code"] = rental_df["zip_code"].astype(str).str.zfill(5)

        # Filter to Chicago zip codes
        rental_df = rental_df[rental_df["zip_code"].isin(chicago_zip_codes)].copy()

        # Time series formatting: convert to long format
        date_cols = [col for col in rental_df.columns if col.startswith("20")]
        long_df = rental_df.melt(
            id_vars=["zip_code"],
            value_vars=date_cols,
            var_name="month",
            value_name="rental_price",
        )

        # Convert month to datetime and sort by zip code and month
        long_df["month"] = pd.to_datetime(long_df["month"])
        long_df = long_df.sort_values(by=["zip_code", "month"])

        logger.info(
            "Missing values before imputation: %d", long_df["rental_price"].isna().sum()
        )

        # Missing value imputation
        long_df["rental_price"] = long_df.groupby("zip_code")["rental_price"].transform(
            lambda x: x.interpolate()
        )
        long_df["rental_price"] = long_df.groupby("zip_code")["rental_price"].transform(
            lambda x: x.ffill()
        )
        long_df["rental_price"] = long_df.groupby("zip_code")["rental_price"].transform(
            lambda x: x.bfill()
        )
        logger.info(
            "Missing values after imputation: %d", long_df["rental_price"].isna().sum()
        )

        logger.info(
            "Loaded %d zip codes with rental data in time series format",
            long_df["zip_code"].nunique(),
        )
        logger.info("Identified %d date columns", len(date_cols))
        logger.info(
            "Date range: %s to %s", long_df["month"].min(), long_df["month"].max()
        )
        logger.info("Total observations: %d", len(long_df))
        logger.info(
            "Rental price range: $%.0f - $%.0f",
            long_df["rental_price"].min(),
            long_df["rental_price"].max(),
        )
        logger.info("Sample data:\n%s", long_df.head())

        # Output the data to a csv file
        output_path = "/project/output/rental_panel_data.csv"
        long_df.to_csv(output_path, index=False)
        logger.info("Saved time series data (at zip code level) to: %s", output_path)
        logger.info(
            "Output shape: %d rows, %d columns",
            len(long_df),
            len(long_df.columns),
        )

        return {"rental_panel_data": long_df}
