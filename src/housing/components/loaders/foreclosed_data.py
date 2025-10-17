"""Foreclosed rental property data loader for Chicago data portal.

This module loads foreclosed rental property data from Chicago's data portal, which provides
addresses, locations, and other details about foreclosures.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt

from housing.components.constants import GEOGRAPHIC_CRS
from pipeline import DataLoader

logger = logging.getLogger(__name__)

class ForeclosedDataLoader(DataLoader):
    """Load foreclosed rental property data from Chicago data portal.

    This demonstrates loading CSV data with geographic points.
    """
    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the foreclosed data loader.

        Args:
            file_path: Optional path to foreclosed data file
        """
        super().__init__(
            "foreclosed_data",
            file_path or "/project/data/Foreclosed_Rental_Property_20251006.csv",
            "Load foreclosed rental property data from Chicago data portal",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean foreclosed rental property data."""
        logger.info("Loading foreclosed data from: %s", self.file_path)

        # Load the CSV data
        foreclosed_df = pd.read_csv(self.file_path)

        # Convert to GeoDataFrame
        foreclosed_df["LOCATION"] = foreclosed_df["LOCATION"].apply(wkt.loads)
        foreclosed_gdf = gpd.GeoDataFrame(foreclosed_df, geometry="LOCATION", crs=GEOGRAPHIC_CRS)

        print(foreclosed_gdf.head())

        return {"foreclosed_data": foreclosed_gdf}

