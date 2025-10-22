"""This loads the data from Affordable_Rental_Housing_Developments.csv into a pandas DataFrame"""

import json
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class AffordableDataLoader(DataLoader):
    """Initialize the component.

    Args:
    file_path: Path to data file (optional)
    """

    def __init__(self, api_url: str | None = None) -> None:
        """Takes filepath (or uses default from .env) of affordable development dataset, and outputs dataset as df"""
        super().__init__(
            "affordable_development_data",
            api_url or "https://data.cityofchicago.org/resource/s6ha-ppgi.json",
            "Load affordable housing development data from City of Chicago API URL",
        )

        self._original_source = api_url or "https://data.cityofchicago.org/resource/s6ha-ppgi.json"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the component logic. Load in and clean the data.

        Args:
            context: Pipeline context with data from previous components

        Returns:
            Dictionary with results to add to context
        """
        logger.info("Loading affordable development data from: %s", self._original_source)

        cache_dir = Path("/project/data/.cache")
        cache_file = cache_dir / "affordable_rental_housing_developments.json"

        # Check if cache exists
        if cache_file.exists():
            logger.info("Loading from cache: %s", cache_file)
            with cache_file.open() as f:
                data = json.load(f)
        else:
            # Fetch from API
            logger.info("Fetching from API (no cache found)...")
            response = requests.get(self._original_source, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Save to cache
            cache_dir.mkdir(parents=True, exist_ok=True)
            with cache_file.open("w") as f:
                json.dump(data, f)
            logger.info("Saved to cache: %s", cache_file)

        affordable_df = pd.read_json(cache_file)

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
