"""This loads the data from Affordable_Rental_Housing_Developments.csv into a pandas DataFrame"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class AffordableDataLoader(DataLoader):
    """Initialize the component.

    Args:
    file_path: Path to data file (optional)
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Takes filepath (or uses default from .env) of affordable development dataset, and outputs dataset as df"""
        super().__init__(
            "affordable_development_data",
            file_path or "/project/data/Affordable_Rental_Housing_Developments.csv",
            "Load affordable housing development data from City of Chicago dataset",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the component logic. Load in and clean the data.

        Args:
            context: Pipeline context with data from previous components

        Returns:
            Dictionary with results to add to context
        """
        logger.info("Loading affordable development data from: %s", self.file_path)

        affordable_df = pd.read_csv(self.file_path)

        logger.info("Cleaning affordable development data")

        def convert_to_snake_case(column_name: str) -> str:
            """Helper function to convert column names to snake case"""
            column_name = column_name.lower()
            column_name = column_name.split(" ")
            return "_".join(column_name)

        affordable_df = affordable_df.rename(columns=convert_to_snake_case)

        affordable_df["property_type"] = affordable_df["property_type"].map(
            {"Multfamily": "Multifamily", "Mutifamily": "Multifamily"}
        )

        # logger.info(
        #     "Loaded %d affordable housing developments with %d with coordinates",
        #     len(affordable_df),
        #     sum(affordable_df["units"]),
        # )

        logger.info("Converting to geoDataFrame ...")

        tract_boundaries = context["tract_boundaries"]

        geo_affordable_df = gpd.GeoDataFrame(
            affordable_df,
            geometry=gpd.points_from_xy(
                affordable_df["longitude"], affordable_df["latitude"]
            ),
            crs=tract_boundaries.crs,
        )

        return {"affordable_developments_data": geo_affordable_df}
