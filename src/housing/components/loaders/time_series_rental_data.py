"""Rental data loader for ZORI dataset.

This module loads rental price data from the Zillow Observed Rent Index (ZORI) dataset,
which provides zip code level rental price estimates. This also formats this into a time series, long format.
"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TimeSeriesRentalDataLoader(DataLoader):
    """Load rental price data from ZORI dataset, reshaped into long format.

    This demonstrates loading CSV data with geographic identifiers (zip codes).
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Load rental data.

        Args:
            file_path: Optional path to rental data file
        """
        super().__init__(
            "rental_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load rental price data from ZORI dataset",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean rental data (put into time series format)."""
        logger.info("Loading rental data from: %s", self.file_path)

        # Load the CSV data
        rental_df = pd.read_csv(self.file_path)

        # Clean and prepare the data
        rental_df = rental_df.rename(columns={"RegionName": "zip_code"})
        rental_df["zip_code"] = rental_df["zip_code"].astype(str).str.zfill(5)

        # Time series formatting: convert to long format
        date_cols = [col for col in rental_df.columns if col.startswith("20")]
        wide_df = rental_df.melt(
            id_vars=["zip_code"],
            value_vars=date_cols,
            var_name="date",
            value_name="rental_price"
        )
        
        print(wide_df.head())

        logger.info("Loaded %d zip codes with rental data in time series format", len(rental_df))
        logger.info(
            "Rental price range: $%.0f - $%.0f",
            wide_df["rental_price"].min(),
            wide_df["rental_price"].max(),
        )

        return {"rental_data": wide_df}