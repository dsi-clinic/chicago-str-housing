"""This loads the data from Affordable_Rental_Housing_Developments.csv into a pandas DataFrame"""

import logging
from typing import Any

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

        affordable_df["Property Type"] = affordable_df["Property Type"].map(
            {"Multfamily": "Multifamily", "Mutifamily": "Multifamily"}
        )

        logger.info(
            "Loaded %d affordable housing developments with %d with coordinates",
            len(affordable_df),
            sum(affordable_df["Units"]),
        )

        return {"affordable_developments_data": affordable_df}
