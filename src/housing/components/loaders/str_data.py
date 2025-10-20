"""STR data loader."""

import logging
import warnings
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


class STRDataLoader(DataLoader):
    """Load STR data (coordinates of prohibited STRs)."""

    def __init__(self, file_path: str | None = None) -> None:
        default_path = (
            "/project/data/House_Share_Prohibited_Buildings_List_20251007.csv"
        )
        super().__init__("str_data", file_path or default_path, "Load STR data")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and convert STR CSV to GeoDataFrame."""
        logger.info("Loading STR data...")

        str_path = getattr(self, "file_path", None)
        if not str_path:
            str_path = (
                "/project/data/House_Share_Prohibited_Buildings_List_20251007.csv"
            )

        str_df = pd.read_csv(str_path)

        # Convert to GeoDataFrame
        str_df["geometry"] = str_df.apply(
            lambda row: Point(row["Longitude"], row["Latitude"]), axis=1
        )
        gdf = gpd.GeoDataFrame(str_df, geometry="geometry")
        gdf = gdf.set_crs("EPSG:4326")

        logger.info("Loaded %d STR coordinates", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        return {"str_data": gdf}
