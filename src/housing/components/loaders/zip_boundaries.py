"""Zip code boundaries loader.

This module loads zip code boundary geometries from CSV files with WKT-encoded polygons.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class ZipBoundariesLoader(DataLoader):
    """Load zip code boundary data.

    This demonstrates loading GeoJSON data with polygon geometries.
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the zip boundaries loader.

        Args:
            file_path: Optional path to zip boundaries file
        """
        super().__init__(
            "zip_boundaries",
            file_path or "/project/data/Boundaries_ZIP_Codes.csv",
            "Load zip code boundary data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load zip code boundaries."""
        logger.info("Loading zip boundaries from: %s", self.file_path)

        # Load CSV with polygon coordinates
        zip_df = pd.read_csv(self.file_path)

        # Convert to GeoDataFrame
        zip_df["geometry"] = zip_df["the_geom"].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(zip_df, geometry="geometry")

        # Set CRS
        gdf = gdf.set_crs("EPSG:4326")

        # Clean zip code column
        if "ZIP" in gdf.columns:
            gdf = gdf.rename(columns={"ZIP": "zip_code"})
        gdf["zip_code"] = gdf["zip_code"].astype(str).str.zfill(5)

        logger.info("Loaded %d zip code boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        return {"zip_boundaries": gdf}
