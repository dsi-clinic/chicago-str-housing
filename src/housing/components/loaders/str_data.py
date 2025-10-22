"""STR data loader."""

import logging
import warnings
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


class STRDataLoader(DataLoader):
    """Load STR data (coordinates of prohibited STRs)."""

    def __init__(
        self,
        api_url: str = "https://data.cityofchicago.org/resource/7bzs-jsyj.json",
        limit: int = 10000,
    ) -> None:
        """Initialize the STR data loader.

        Args:
            api_url: City of Chicago Open Data API endpoint
            limit: Maximum number of records to fetch (default: 10,000)
        """
        super().__init__("str_data", api_url, "Load STR data from API")

        self.api_url = api_url
        self.limit = limit

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Fetch STR data from API."""
        logger.info("Fetching STR data from API: %s", self.api_url)

        try:
            params = {"$limit": self.limit}
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            str_df = pd.DataFrame(data)
            logger.info("Fetched %d STR records", len(str_df))
        except Exception as e:
            logger.error("Failed to fetch STR data: %s", e)
            raise

        # Clean data, drop rows with either no latitude or longitude, drop older duplicates if there is one
        initial_str_len = len(str_df)
        str_df = str_df.dropna(subset=["latitude", "longitude"])
        str_df["effective_date"] = str_df["signed_date"].fillna(str_df["recorded_date"])
        str_df["effective_date"] = pd.to_datetime(
            str_df["effective_date"], errors="coerce"
        )
        str_df = str_df.dropna(subset=["effective_date"])
        str_df = str_df.sort_values(
            by="effective_date", ascending=False
        ).drop_duplicates(subset=["latitude", "longitude"], keep="first")
        logger.info("Dropped %d rows after cleaning", initial_str_len - len(str_df))

        # Convert to GeoDataFrame
        str_df["geometry"] = str_df.apply(
            lambda row: Point(row["longitude"], row["latitude"]), axis=1
        )
        gdf = gpd.GeoDataFrame(str_df, geometry="geometry")
        gdf = gdf.set_crs("EPSG:4326")

        logger.info("Loaded %d STR coordinates", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        return {"str_data": gdf}
