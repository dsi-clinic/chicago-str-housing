"""American Community Survey Data Loader

Loading Population and socioeconomic indicators using API
"""

import csv
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("CENSUS_API_KEY")

BASE_URL = "https://api.census.gov/data/2023/acs/acs5"

# Census Name and Numerical Variables
# Name, Total Population, Median Household Income
num_ind = ["NAME", "B01003_001E", "B19013_001E"]

# Categorical Variables

# Year Structure Built
# Total, 2020 or later, 2010-2019, 2000-2009
year_built_ind = ["B25034_001E", "B25034_002E", "B25034_003E", "B25034_004E"]

# Tenure
# Total, renter-occupied
tenure_ind = ["B25003_001E", "B25003_003E"]

# Means of Transportation to Work
# Total, Car truck van, Public Transportation, Walk, Work From Home
transport_ind = [
    "B08301_001E",
    "B08301_002E",
    "B08301_010E",
    "B08301_019E",
    "B08301_021E",
]

variables = num_ind + year_built_ind + tenure_ind + transport_ind
indicators = ",".join(variables)

FULL_URL = (
    f"{BASE_URL}?get={indicators}&for=tract:*&in=state:17+county:031&key={API_KEY}"
)


class ACSLoader(DataLoader):
    """Load ACS Data data from API.

    This demonstrates loading census tract geometries for more granular analysis.
    Census tracts are smaller than community areas and standardized across the US.
    Data source:
    - US Census Bureau TIGER/Line 2023 (matches 2019-2023 ACS 5-year estimates)
    - Download: https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2023&layergroup=Census+Tracts
    - Select Illinois to get tl_2023_17_tract.zip
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the ACS loader.

        Args:
            file_path: Optional path to FULL URL API
        """
        source = file_path or FULL_URL
        super().__init__(
            "acs_data",
            source,
            "Load ACS data",
        )
        # Store the original URL string (base class converts to Path which mangles URLs)
        self._original_source = source

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load ACS Data."""
        # not showing whole cache due to API Keys
        logger.info("Loading ACS Data from: %s...", self._original_source[:50])

        # Check if loading from URL or file
        if self._original_source.startswith(
            "http://"
        ) or self._original_source.startswith("https://"):
            # Set up cache file path
            cache_dir = Path("/project/data/.cache")
            cache_file = cache_dir / "acs_data.csv"

            # Check if cache exists
            if cache_file.exists():
                logger.info("Loading from cache: %s", cache_file)
                acs_data = pd.read_csv(cache_file)
            else:
                # Fetch from API
                logger.info("Fetching from API (no cache found)...")
                response = requests.get(self._original_source, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Save to cache
                cache_dir.mkdir(parents=True, exist_ok=True)
                with cache_file.open("w") as f:
                    writer = csv.writer(f)
                    writer.writerows(data)
                logger.info("Saved to cache: %s", cache_file)

                acs_data = pd.DataFrame(data[1:], columns=data[0])

        else:
            acs_data = pd.read_csv(self._original_source)

        # Standardize column names
        acs_data = acs_data.rename(
            columns={
                "NAME": "census_full_name",
                "B01003_001E": "population",
                "B19013_001E": "median_house_income",
                "B25034_001E": "total_house_built",
                "B25034_002E": "2020_or_later",
                "B25034_003E": "2010_2019",
                "B25034_004E": "2000_2009",
                "B25003_001E": "total_tenure",
                "B25003_003E": "renter_occupied",
                "B08301_001E": "total_transportation",
                "B08301_002E": "car_truck_van",
                "B08301_010E": "public_transportation",
                "B08301_019E": "walk",
                "B08301_021E": "work_from_home",
            }
        )

        # Clean DataFrame
        acs_data["median_house_income"] = acs_data["median_house_income"].replace(
            -666666666, np.nan
        )

        # Create GEOID for Spatial Join
        acs_data["GEOID"] = (
            acs_data["state"].astype(str)
            + acs_data["county"].astype(str).str.zfill(3)
            + acs_data["tract"].astype(str).str.zfill(6)
        )

        logger.info("Load %d ACS data", len(acs_data))
        logger.info("=" * 45)
        return {"acs_data": acs_data}
