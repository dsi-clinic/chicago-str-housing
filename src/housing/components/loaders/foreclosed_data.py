"""Foreclosed rental property data loader.

This module loads date of recently foreclosed rental properties from Chicago's data portal API.
"""

import json
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
from shapely import wkt

from pipeline.base import DataLoader

DEFAULT_FORECLOSED_URL = "https://data.cityofchicago.org/resource/yhcw-iu53.json"

logger = logging.getLogger(__name__)


class ForeclosedDataLoader(DataLoader):
    """Load foreclosed rental property data from API.

    Converts data to GeoDataFrame for spatial analysis.
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the foreclosed data loader."""
        source = file_path or DEFAULT_FORECLOSED_URL
        super().__init__(
            "foreclosed_data",
            source,
            "Load foreclosed rental data",
        )
        # Store the original URL string (base class converts to Path which mangles URLs)
        self._original_source = source

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load foreclosed rental property data."""
        logger.info("Loading foreclosed rental data from: %s", self._original_source)

        # Set up cache file path
        cache_dir = Path("/project/data/.cache")
        cache_file = cache_dir / "foreclosed_data.json"

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
            logger.info("Data cached to: %s", cache_file)

        # Parse the JSON response
        # Chicago Data Portal returns a list with one feature
        if not data or len(data) == 0:
            logger.warning("No foreclosed data found from source.")

        # Convert to DataFrame and clean
        foreclosed_df = pd.DataFrame(data)
        foreclosed_df["location"] = foreclosed_df["location"].apply(wkt.loads)

        # Convert to GeoDataFrame and remove unnecessary columns
        foreclosed_gdf = gpd.GeoDataFrame(
            foreclosed_df, geometry="location", crs="EPSG:4326"
        )
        foreclosed_gdf["chicago_owner"] = (
            foreclosed_gdf["owner_city"].str.lower() == "chicago"
        )
        foreclosed_gdf["il_owner"] = foreclosed_gdf["owner_state"].str.lower() == "il"
        foreclosed_gdf["chicago_mgmt"] = (
            foreclosed_gdf["owner_management_agent_city"].str.lower() == "chicago"
        )
        foreclosed_gdf["il_mgmt"] = (
            foreclosed_gdf["owner_management_agent_state"].str.lower() == "il"
        )

        foreclosed_gdf["owner_date"] = pd.to_datetime(
            foreclosed_gdf["owner_date"], errors="coerce"
        ).dt.date

        foreclosed_gdf["submission_date"] = pd.to_datetime(
            foreclosed_gdf["submission_date"], errors="coerce"
        ).dt.date

        foreclosed_gdf = foreclosed_gdf.drop(
            columns=[
                "owner_management_agent_name",
                "owner_notices_agent_name",
                "owner_notices_agent_phone",
                "owner_notices_agent_email",
                "owner_address",
                "owner_zip",
                "owner_management_agent_zip",
                "owner_city",
                "owner_state",
                "owner_management_agent_city",
                "owner_management_agent_state",
                "owner_management_agent_address",
            ]
        )

        return {"foreclosed_data": foreclosed_gdf}
