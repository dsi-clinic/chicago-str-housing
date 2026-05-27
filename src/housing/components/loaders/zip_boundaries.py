"""Zip code boundaries loader.

This module loads zip code boundary geometries from the Chicago Data Portal JSON API.
"""

import json
import logging
from typing import Any

import geopandas as gpd
import requests
from shapely.geometry import shape

from pipeline.base import DataLoader
from pipeline.config import default_data_dir

logger = logging.getLogger(__name__)

# Chicago Data Portal JSON endpoint for ZIP codes
DEFAULT_ZIP_CODES_URL = "https://data.cityofchicago.org/resource/unjd-c2ca.json"


class ZipBoundariesLoader(DataLoader):
    """Load zip code boundary data from Chicago Data Portal.

    Loads GeoJSON data from the Chicago Data Portal API endpoint.
    The endpoint provides ZIP code boundaries with geometry and metadata.

    Data source: https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-ZIP-Codes/gdcf-axmw
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the zip boundaries loader.

        Args:
            file_path: Optional path to zip boundaries file or URL
                       Default: Chicago Data Portal JSON endpoint
        """
        source = file_path or DEFAULT_ZIP_CODES_URL
        super().__init__(
            "zip_boundaries",
            source,
            "Load zip code boundary data",
        )
        # Store the original URL string (base class converts to Path which mangles URLs)
        self._original_source = source

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load zip code boundaries."""
        logger.info("Loading zip boundaries from: %s", self._original_source)

        # Check if loading from URL or file
        if self._original_source.startswith(
            "http://"
        ) or self._original_source.startswith("https://"):
            # Set up cache file path
            cache_dir = default_data_dir() / ".cache"
            cache_file = cache_dir / "zip_boundaries.json"

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

            # Convert GeoJSON geometries to shapely objects
            geometries = [shape(item["the_geom"]) for item in data]

            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

            # Drop the original GeoJSON column
            if "the_geom" in gdf.columns:
                gdf = gdf.drop(columns=["the_geom"])
        else:
            # Load from local file (fallback)
            gdf = gpd.read_file(self._original_source)

        # Standardize zip code column
        # API returns "zip" column
        if "zip" in gdf.columns:
            gdf["zip_code"] = gdf["zip"]
        elif "ZIP" in gdf.columns:
            gdf["zip_code"] = gdf["ZIP"]

        # Ensure zip codes are 5-digit strings with leading zeros
        if "zip_code" in gdf.columns:
            gdf["zip_code"] = gdf["zip_code"].astype(str).str.zfill(5)

        # Ensure CRS is set
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")

        logger.info("Loaded %d zip code boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        if "zip_code" in gdf.columns:
            logger.info(
                "ZIP codes: %s to %s",
                gdf["zip_code"].min(),
                gdf["zip_code"].max(),
            )

        return {"zip_boundaries": gdf}
