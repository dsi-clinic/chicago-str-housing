"""City boundaries data loader.

This module loads the Chicago city boundary from the Chicago Data Portal API.
"""

import json
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests
from shapely.geometry import shape

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class CityBoundariesLoader(DataLoader):
    """Load Chicago city boundaries from API.

    Fetches the city boundary from the Chicago Data Portal API and caches it locally.
    The boundary is used to clip census tract maps to show only Chicago proper.
    """

    def __init__(
        self, file_path: str = "https://data.cityofchicago.org/resource/qqq8-j68g.json"
    ) -> None:
        """Initialize the city boundaries loader.

        Args:
            file_path: URL to the city boundaries API endpoint
        """
        super().__init__(
            "city_boundaries", "Load Chicago city boundaries from API", file_path
        )
        self._original_source = file_path

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load city boundaries from API with caching."""
        # Use the original source URL instead of the converted Path
        file_path_str = str(self._original_source)

        # Check if this is an API URL
        if file_path_str.startswith("http://") or file_path_str.startswith("https://"):
            logger.info("Loading city boundaries from: %s", file_path_str)

            # Set up cache directory and file
            cache_dir = Path("/project/data/.cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "city_boundaries.json"

            # Check if we have a cached version
            if cache_file.exists():
                logger.info("Loading from cache: %s", cache_file)
                with cache_file.open("r") as f:
                    data = json.load(f)
            else:
                # Fetch from API
                response = requests.get(file_path_str, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Cache the response
                with cache_file.open("w") as f:
                    json.dump(data, f)
                logger.info("Cached city boundaries to: %s", cache_file)

            # Parse the JSON response
            # Chicago Data Portal returns a list with one feature
            if not data or len(data) == 0:
                msg = "No city boundary data received from API"
                raise ValueError(msg)

            feature = data[0]

            # Extract geometry
            geometry = shape(feature["the_geom"])

            # Create GeoDataFrame
            city_gdf = gpd.GeoDataFrame(
                [{"name": feature.get("name", "Chicago"), "geometry": geometry}],
                crs="EPSG:4326",
            )

        else:
            # Fallback: load from local file if provided
            city_gdf = gpd.read_file(str(self.file_path))

        logger.info("Loaded city boundary: %s", city_gdf["name"].iloc[0])
        logger.info("CRS: %s", city_gdf.crs)
        logger.info(
            "Boundary area: %.2f km²", city_gdf.geometry.area.sum() * 111 * 111
        )  # Rough conversion from degrees² to km²

        return {"city_boundaries": city_gdf}
