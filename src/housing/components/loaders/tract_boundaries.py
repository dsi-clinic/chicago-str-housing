"""Census tract boundaries loader.

This module loads census tract boundary geometries for fine-grained spatial analysis.
"""

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class TractBoundariesLoader(DataLoader):
    """Load census tract boundary data.

    This demonstrates loading census tract geometries for more granular analysis.
    Census tracts are smaller than community areas and standardized across the US.

    Data can be obtained from:
    - Chicago Data Portal: https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Census-Tracts-2010/5jrd-6zik
    - US Census Bureau TIGER/Line: https://www.census.gov/cgi-bin/geo/shapefiles/index.php
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the tract boundaries loader.

        Args:
            file_path: Optional path to tract boundaries file
        """
        super().__init__(
            "tract_boundaries",
            file_path or "/project/data/Boundaries_Census_Tracts.csv",
            "Load census tract boundary data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load census tract boundaries."""
        logger.info("Loading census tract boundaries from: %s", self.file_path)

        # Check if file exists
        if not Path(self.file_path).exists():
            error_msg = (
                f"Census tract boundaries file not found: {self.file_path}\n"
                "Please download from:\n"
                "  - Chicago Data Portal: https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Census-Tracts-2010/5jrd-6zik\n"
                "  - Export as CSV and save to /project/data/Boundaries_Census_Tracts.csv"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Load CSV with polygon coordinates
        tract_df = pd.read_csv(self.file_path)

        # Convert to GeoDataFrame
        # Assuming 'the_geom' column contains WKT geometries (similar to other boundary files)
        if "the_geom" in tract_df.columns:
            tract_df["geometry"] = tract_df["the_geom"].apply(wkt.loads)
        elif "geometry" in tract_df.columns:
            tract_df["geometry"] = tract_df["geometry"].apply(wkt.loads)
        else:
            raise ValueError("No geometry column found in census tract data")

        gdf = gpd.GeoDataFrame(tract_df, geometry="geometry")

        # Set CRS
        gdf = gdf.set_crs("EPSG:4326")

        # Standardize tract identifier column
        # Different sources may have different column names
        for col in ["GEOID10", "geoid10", "TRACTCE10", "tract", "GEOID", "geoid"]:
            if col in gdf.columns:
                gdf = gdf.rename(columns={col: "tract_geoid"})
                break

        # Ensure tract_geoid is string
        if "tract_geoid" in gdf.columns:
            gdf["tract_geoid"] = gdf["tract_geoid"].astype(str)

        logger.info("Loaded %d census tract boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)
        if "tract_geoid" in gdf.columns:
            logger.info("Sample tract GEOIDs: %s", gdf["tract_geoid"].head(3).tolist())

        return {"tract_boundaries": gdf}
