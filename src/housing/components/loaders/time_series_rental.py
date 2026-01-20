"""Time series rental data loader for ZORI dataset.

This module loads rental price data from the Zillow Observed Rent Index (ZORI) dataset,
which provides zip code level rental price estimates.
"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TimeSeriesRentalLoader(DataLoader):
    """Load rental price data from ZORI dataset.

    This demonstrates loading CSV data with geographic identifiers (zip codes).
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the rental data loader.

        Args:
            file_path: Optional path to rental data file
        """
        super().__init__(
            "rental_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
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

        # Keep only Chicago zip codes
        zip_boundaries = context["zip_boundaries"]
        zip_rental = zip_boundaries.merge(rental_df, on="zip_code", how="inner")

        logger.info("Loaded %d zip codes with rental data", len(zip_rental))

        return {"rental_data": zip_rental}
