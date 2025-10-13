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

    Data source:
    - US Census Bureau TIGER/Line 2023 (matches 2019-2023 ACS 5-year estimates)
    - Download: https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2023&layergroup=Census+Tracts
    - Select Illinois to get tl_2023_17_tract.zip
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the tract boundaries loader.

        Args:
            file_path: Optional path to tract boundaries shapefile
                       Default: /project/data/tl_2023_17_tract/tl_2023_17_tract.shp
        """
        super().__init__(
            "tract_boundaries",
            file_path or "/project/data/tl_2023_17_tract/tl_2023_17_tract.shp",
            "Load census tract boundary data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load census tract boundaries."""
        logger.info("Loading census tract boundaries from: %s", self.file_path)

        # Check if file exists
        if not Path(self.file_path).exists():
            error_msg = (
                f"Census tract boundaries file not found: {self.file_path}\n"
                "Please download 2023 TIGER/Line shapefiles from:\n"
                "  https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2023&layergroup=Census+Tracts\n"
                "  1. Select Illinois\n"
                "  2. Download tl_2023_17_tract.zip to /project/data/\n"
                "  3. Extract to a subdirectory:\n"
                "     unzip tl_2023_17_tract.zip -d /project/data/tl_2023_17_tract/\n"
                "  OR double-click the zip file (creates tl_2023_17_tract/ folder automatically)"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Load shapefile (or fallback to CSV if provided)
        file_ext = Path(self.file_path).suffix.lower()

        if file_ext == ".shp":
            # Load TIGER/Line shapefile
            try:
                gdf = gpd.read_file(self.file_path)
            except Exception as e:
                # Check if companion files are missing
                shp_path = Path(self.file_path)
                companion_files = [
                    shp_path.with_suffix(".shx"),
                    shp_path.with_suffix(".dbf"),
                    shp_path.with_suffix(".prj"),
                ]
                missing_files = [f for f in companion_files if not f.exists()]

                if missing_files:
                    missing_names = [f.name for f in missing_files]
                    error_msg = (
                        f"Shapefile companion files missing: {', '.join(missing_names)}\n"
                        "Shapefiles require multiple files (.shp, .shx, .dbf, .prj, .cpg)\n"
                        "Please extract ALL files from tl_2023_17_tract.zip to:\n"
                        "  /project/data/tl_2023_17_tract/\n"
                        "  OR double-click the zip file to extract automatically"
                    )
                    logger.error(error_msg)
                    raise FileNotFoundError(error_msg) from e
                else:
                    # Some other error
                    raise

            # Filter to Cook County (Chicago) only
            if "COUNTYFP" in gdf.columns:
                gdf = gdf[gdf["COUNTYFP"] == "031"].copy()
                logger.info("Filtered to Cook County (Chicago)")

            # Use GEOID as tract identifier (11-digit: State+County+Tract)
            if "GEOID" in gdf.columns:
                gdf["tract_geoid"] = gdf["GEOID"]

        elif file_ext == ".csv":
            # Legacy: support CSV with WKT geometries
            tract_df = pd.read_csv(self.file_path)

            if "the_geom" in tract_df.columns:
                tract_df["geometry"] = tract_df["the_geom"].apply(wkt.loads)
            elif "geometry" in tract_df.columns:
                tract_df["geometry"] = tract_df["geometry"].apply(wkt.loads)
            else:
                raise ValueError("No geometry column found in census tract data")

            gdf = gpd.GeoDataFrame(tract_df, geometry="geometry")
            gdf = gdf.set_crs("EPSG:4326")

            # Try to identify tract ID column
            for col in ["GEOID10", "geoid10", "GEOID", "geoid", "TRACTCE10", "tract"]:
                if col in gdf.columns:
                    gdf["tract_geoid"] = gdf[col]
                    break
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Use .shp or .csv")

        # Ensure tract_geoid is string
        if "tract_geoid" in gdf.columns:
            gdf["tract_geoid"] = gdf["tract_geoid"].astype(str)
        else:
            logger.warning("No tract_geoid column created - check your data")

        logger.info("Loaded %d census tract boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)
        if "tract_geoid" in gdf.columns:
            logger.info("Sample tract GEOIDs: %s", gdf["tract_geoid"].head(3).tolist())

        return {"tract_boundaries": gdf}
