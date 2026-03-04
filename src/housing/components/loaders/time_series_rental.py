"""Time series rental data loader for ZORI dataset.

This module loads rental price data from the Zillow Observed Rent Index (ZORI) dataset,
which provides zip code level rental price estimates.

It then converts the data to a panel time-series dataset.
"""

import logging
from typing import Any

import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


def _identify_date_columns(df: pd.DataFrame) -> list[str]:
    """Identify date columns in the rental data.

    ZORI dataset uses date columns starting with "20" (e.g., "2010-01", "2020-12").
    This function filters columns that start with "20" to identify time series columns.

    Args:
        df: DataFrame containing rental data with potential date columns

    Returns:
        List of column names that represent date columns
    """
    return [col for col in df.columns if col.startswith("20")]


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
            "rental_panel_data",
            file_path or "/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv",
            "Load rental price data from ZORI dataset and create a panel timeseries dataframe",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean rental data."""
        logger.info("Loading rental data from: %s", self.file_path)

        # Load the CSV data
        rental_df = pd.read_csv(self.file_path)

        # Clean and prepare the data
        rental_df = rental_df.rename(columns={"RegionName": "zip_code"})
        rental_df["zip_code"] = rental_df["zip_code"].astype(str).str.zfill(5)

        # Identify date columns
        date_cols = _identify_date_columns(rental_df)
        logger.info("Identified %d date columns", len(date_cols))

        # Keep only Chicago zip codes
        zip_boundaries = context["zip_boundaries"]
        zip_rental = zip_boundaries.merge(rental_df, on="zip_code", how="inner")

        logger.info("Loaded %d zip codes with rental data", len(zip_rental))

        # Melt dataframe to panel dataset format
        rental_panel_data = pd.melt(
            zip_rental,
            id_vars="zip_code",
            value_vars=date_cols,
            var_name="month",
            value_name="rental_price",
        )

        # convert to datetime dtype
        rental_panel_data["month"] = pd.to_datetime(rental_panel_data["month"])

        logger.info(
            "Date range: %s to %s",
            rental_panel_data["month"].min(),
            rental_panel_data["month"].max(),
        )
        logger.info("Total observations: %d", len(rental_panel_data))

        # impute missing data
        logger.info(
            "Missing values before imputation: %d",
            rental_panel_data["rental_price"].isna().sum(),
        )

        # Sort first to ensure correct order
        rental_panel_data = rental_panel_data.sort_values(["zip_code", "month"])

        # Interpolate missing values within each ZIP code
        rental_panel_data["rental_price"] = rental_panel_data.groupby("zip_code")[
            "rental_price"
        ].transform(lambda x: x.interpolate(method="linear"))

        # For any remaining NaNs at the edges, forward/backward fill
        rental_panel_data["rental_price"] = rental_panel_data.groupby("zip_code")[
            "rental_price"
        ].transform(lambda x: x.ffill().bfill())

        logger.info(
            "Missing values after imputation: %d",
            rental_panel_data["rental_price"].isna().sum(),
        )

        return {"rental_panel_data": rental_panel_data}
