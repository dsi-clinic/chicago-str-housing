"""Community area boundaries loader.

This module loads Chicago community area boundary geometries from the
Chicago Data Portal JSON API.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests
from shapely.geometry import shape

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)

# Chicago Data Portal JSON endpoint for community areas
DEFAULT_COMMUNITY_AREAS_URL = "https://data.cityofchicago.org/resource/igwz-8jzy.json"


class CommunityBoundariesLoader(DataLoader):
    """Load community area boundary data from Chicago Data Portal.

    Loads GeoJSON data from the Chicago Data Portal API endpoint.
    The endpoint provides community area boundaries with geometry and metadata.

    Data source: https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/cauq-8yn6
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the community boundaries loader.

        Args:
            file_path: Optional path to community boundaries file or URL
                       Default: Chicago Data Portal JSON endpoint
        """
        source = file_path or DEFAULT_COMMUNITY_AREAS_URL
        super().__init__(
            "community_boundaries",
            source,
            "Load community area boundary data",
        )
        # Store the original URL string (base class converts to Path which mangles URLs)
        self._original_source = source

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load community area boundaries."""
        logger.info("Loading community boundaries from: %s", self._original_source)

        # Check if loading from URL or file
        if self._original_source.startswith(
            "http://"
        ) or self._original_source.startswith("https://"):
            # Set up cache file path
            cache_dir = Path(os.environ.get("DATA_DIR", "/project/data")) / ".cache"
            cache_file = cache_dir / "community_boundaries.json"

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

        # Standardize column names
        # area_numbe: area number (1-77)
        # community: community name (e.g., "EDGEWATER")
        if "area_numbe" in gdf.columns:
            gdf["community_area"] = gdf["area_numbe"]

        if "community" in gdf.columns:
            gdf["community_name"] = gdf["community"]
        elif "COMMUNITY" in gdf.columns:
            gdf["community_name"] = gdf["COMMUNITY"]

        # Ensure CRS is set
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")

        logger.info("Loaded %d community area boundaries", len(gdf))
        logger.info("CRS: %s", gdf.crs)

        if "community_area" in gdf.columns:
            logger.info(
                "Community areas: %s to %s",
                gdf["community_area"].min(),
                gdf["community_area"].max(),
            )

        return {"community_boundaries": gdf}
