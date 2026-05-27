"""Rental data loader for ZORI dataset.

This module loads rental price data from the Zillow Observed Rent Index (ZORI) dataset,
which provides zip code level rental price estimates.
"""

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class RentalDataLoader(DataLoader):
    """Load rental price data from ZORI dataset.

    This demonstrates loading CSV data with geographic identifiers (zip codes).
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the rental data loader.

        Args:
            file_path: Optional path to rental data file
        """
        default_zori = (
            Path(os.environ.get("DATA_DIR", "/project/data"))
            / "Zip_zori_uc_sfrcondomfr_sm_month.csv"
        )
        super().__init__(
            "rental_data",
            str(file_path) if file_path else str(default_zori),
            "Load rental price data from ZORI dataset",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean rental data."""
        logger.info("Loading rental data from: %s", self.file_path)

        # Load the CSV data
        rental_df = pd.read_csv(self.file_path)

        # Clean and prepare the data
        rental_df = rental_df.rename(columns={"RegionName": "zip_code"})
        rental_df["zip_code"] = rental_df["zip_code"].astype(str).str.zfill(5)

        # Get the most recent month's data
        date_columns = [col for col in rental_df.columns if col.startswith("20")]
        if date_columns:
            latest_month = sorted(date_columns)[-1]
            rental_df = rental_df[["zip_code", latest_month]].copy()
            rental_df = rental_df.rename(columns={latest_month: "rental_price"})
            rental_df = rental_df.dropna()

        logger.info("Loaded %d zip codes with rental data", len(rental_df))
        logger.info(
            "Rental price range: $%.0f - $%.0f",
            rental_df["rental_price"].min(),
            rental_df["rental_price"].max(),
        )

        return {"rental_data": rental_df}
