"""Time series rental data loader.

This module loads rental price data from the Zillow Observed Rent Index (ZORI) dataset,
which provides zip code level rental price estimates.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TimeSeriesRentalLoader(DataLoader):
    """Load time series rental data from ZORI dataset.

    This demonstrates loading CSV data with geographic identifiers (zip codes).
    """

    def __init__(
        self, file_path: str | None = None, output_dir: str | None = None
    ) -> None:
        """Initialize the time series rental loader.

        Args:
            file_path: Optional path to rental data file
            output_dir: Optional output directory for rental data
        """
        super().__init__(
            "rental_panel_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load time series rental data from ZORI dataset",
        )
        self.output_dir = output_dir

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean time series rental data."""
        logger.info("Loading time series rental data from: %s", self.file_path)

        # Load the CSV data
        rental_wide_df = pd.read_csv(self.file_path)

        # Clean and prepare the data
        rental_wide_df = rental_wide_df.rename(columns={"RegionName": "zip_code"})
        rental_wide_df["zip_code"] = rental_wide_df["zip_code"].astype(str).str.zfill(5)

        logger.info(
            "Loaded %d zip codes with time series rental data", len(rental_wide_df)
        )

        # Convert from wide to long format
        date_cols = [col for col in rental_wide_df.columns if col.startswith("20")]

        logger.info("Identified %d date columns", len(date_cols))

        rental_long_df = rental_wide_df.melt(
            id_vars=["zip_code"],
            value_vars=date_cols,
            var_name="month",
            value_name="rental_price",
        )

        # Convert "month" column to datetime
        rental_long_df["month"] = pd.to_datetime(rental_long_df["month"])

        logger.info(
            "Date range: %s to %s",
            rental_long_df["month"].min(),
            rental_long_df["month"].max(),
        )
        logger.info("Total observations: %d", len(rental_long_df))

        # Sort by ZIP code and month
        rental_long_df = rental_long_df.sort_values(by=["zip_code", "month"])

        # Linearly interpolate missing values within each ZIP code
        logger.info(
            "Missing values before imputation: %d",
            rental_long_df["rental_price"].isna().sum(),
        )
        rental_long_df["rental_price"] = rental_long_df.groupby("zip_code")[
            "rental_price"
        ].transform(lambda x: x.interpolate(method="linear"))

        # For any NaN values at the edges, forward or backward fill
        rental_long_df["rental_price"] = rental_long_df.groupby("zip_code")[
            "rental_price"
        ].transform(lambda x: x.ffill().bfill())

        if self.output_dir is not None:
            output_path = Path(self.output_dir) / "rental_panel_data.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            rental_long_df.to_csv(output_path, index=False)
            logger.info("Saved rental panel data to: %s", output_path)

        return {"rental_panel_data": rental_long_df}
