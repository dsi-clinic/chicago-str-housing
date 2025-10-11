"""Community area boundaries loader.

This module loads Chicago community area boundary geometries.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class CommunityBoundariesLoader(DataLoader):
    """Load community area boundary data.

    This demonstrates loading CSV data with polygon coordinates that need
    to be converted to GeoDataFrame.
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the community boundaries loader.

        Args:
            file_path: Optional path to community boundaries file
        """
        super().__init__(
            "community_boundaries",
            file_path or "/project/data/Boundaries_Community_Areas.csv",
            "Load community area boundary data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load community area boundaries."""
        logger.info("Loading community boundaries from: %s", self.file_path)

        # Load CSV with polygon coordinates
        community_df = pd.read_csv(self.file_path)

        # Convert to GeoDataFrame
        community_df["geometry"] = community_df["the_geom"].apply(wkt.loads)
        gdf = gpd.GeoDataFrame(community_df, geometry="geometry")

        # Set CRS
        gdf = gdf.set_crs("EPSG:4326")

        # Clean column names
        gdf = gdf.rename(columns={"COMMUNITY": "community_name"})

        logger.info("Loaded %d community area boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        return {"community_boundaries": gdf}
