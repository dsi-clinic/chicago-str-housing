"""Census data loader for 2023 ACS data.

This module loads demographic and economic data from the 2023 American Community Survey (ACS)
including median income, median house value, median age, percentage with bachelor's degree,
and population for calculating population density by census tract.
"""

import logging
import os
from typing import Any

import pandas as pd
import requests

from pipeline.base import DataLoader

# Constants
MIN_API_RESPONSE_LENGTH = 2  # Header row + at least one data row

# Bundled key for local/demo parity when ``CENSUS_API_KEY`` is unset; prefer env in production.
_LEGACY_DEMO_CENSUS_API_KEY = "2a9cd1fa2e1158252a3f3810be0589b6d9ef41a0"

logger = logging.getLogger(__name__)


def resolve_census_api_key(explicit: str | None = None) -> str | None:
    """Resolve Census Bureau API key: explicit arg, then ``CENSUS_API_KEY``, then legacy demo."""
    if explicit:
        return explicit
    env_key = os.environ.get("CENSUS_API_KEY")
    if env_key:
        return env_key
    logger.warning(
        "CENSUS_API_KEY not set; using bundled demo key for ACS fetches. "
        "Set CENSUS_API_KEY in the environment for production.",
    )
    return _LEGACY_DEMO_CENSUS_API_KEY


class CensusDataLoader(DataLoader):
    """Load 2023 ACS census data for Chicago area.

    Loads demographic and economic data from the U.S. Census Bureau API
    for census tracts in Illinois (specifically Chicago area).
    """

    def __init__(
        self,
        api_key: str | None = None,
        state_fips: str = "17",  # Illinois FIPS code
        county_fips: str | None = None,  # Cook County = "031", None for all counties
    ) -> None:
        """Initialize the census data loader.

        Args:
            api_key: Census API key (if None, will try to get from environment)
            state_fips: State FIPS code (default: "17" for Illinois)
            county_fips: County FIPS code (default: None for all counties in state)
        """
        super().__init__(
            "census_data",
            "census_api",  # Not a file path, but identifier
            "Load 2023 ACS census data from U.S. Census Bureau API",
        )
        self.api_key = api_key
        self.state_fips = state_fips
        self.county_fips = county_fips

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load 2023 ACS census data from Census API."""
        logger.info("Fetching 2023 ACS census data from Census API")

        api_key = resolve_census_api_key(
            self.api_key or context.get("census_api_key"),
        )
        if not api_key:
            logger.warning(
                "No Census API key provided. Using demo mode with limited data."
            )
            # For demo purposes, we'll create sample data
            return self._create_demo_data()

        # Define the variables we want to fetch
        variables = [
            "B19013_001E",  # Median household income
            "B25077_001E",  # Median value of owner-occupied housing units
            "B01002_001E",  # Median age
            "B15003_022E",  # Bachelor's degree (25+ years)
            "B15003_001E",  # Total population 25+ years
            "B01003_001E",  # Total population
            "B25003_001E",  # Total occupied housing units
            "B25003_002E",  # Owner-occupied housing units
            "NAME",  # Geographic name
        ]

        try:
            # Construct API URL
            base_url = "https://api.census.gov/data/2023/acs/acs5"

            # Build geographic filter
            # Census API expects separate 'for' and 'in' parameters
            params = {
                "get": ",".join(variables),
                "for": "tract:*",
                "in": f"state:{self.state_fips}",
            }

            if self.county_fips:
                params["in"] += f" county:{self.county_fips}"

            # Add API key
            params["key"] = api_key

            logger.info("Making Census API request for Illinois census tracts")
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Convert to DataFrame
            if not data or len(data) < MIN_API_RESPONSE_LENGTH:
                logger.error("No data returned from Census API")
                return {"census_data": pd.DataFrame()}

            # First row contains column names
            columns = data[0]
            census_df = pd.DataFrame(data[1:], columns=columns)

            logger.info("Fetched %d census tracts", len(census_df))

        except Exception as e:
            logger.error("Failed to fetch census data: %s", e)
            logger.info("Falling back to demo data")
            return self._create_demo_data()

        # Clean and process the data
        census_df = self._process_census_data(census_df)

        # Log summary statistics
        self._log_summary_stats(census_df)

        return {"census_data": census_df}

    def _process_census_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean the census data."""
        # Convert numeric columns
        numeric_columns = [
            "B19013_001E",  # Median household income
            "B25077_001E",  # Median house value
            "B01002_001E",  # Median age
            "B15003_022E",  # Bachelor's degree count
            "B15003_001E",  # Total 25+ population
            "B01003_001E",  # Total population
            "B25003_001E",  # Total occupied housing units
            "B25003_002E",  # Owner-occupied housing units
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                # Replace Census API sentinel values with NaN
                # -666666666 means data not available
                df[col] = df[col].replace(-666666666, float("nan"))

        # Calculate percentage with bachelor's degree
        if "B15003_022E" in df.columns and "B15003_001E" in df.columns:
            df["pct_bachelor"] = (df["B15003_022E"] / df["B15003_001E"] * 100).round(2)
            # Handle division by zero and missing data
            df["pct_bachelor"] = df["pct_bachelor"].fillna(0)

        # Calculate percentage of rented households
        if "B25003_001E" in df.columns and "B25003_002E" in df.columns:
            # pct_rented = ((total occupied - owner occupied) / total occupied) * 100
            df["pct_rented"] = (
                (df["B25003_001E"] - df["B25003_002E"]) / df["B25003_001E"] * 100
            ).round(2)
            # Handle division by zero and missing data
            df["pct_rented"] = df["pct_rented"].fillna(0)

        # Rename columns to more readable names
        column_mapping = {
            "B19013_001E": "median_income",
            "B25077_001E": "median_house_value",
            "B01002_001E": "median_age",
            "B15003_022E": "bachelor_count",
            "B15003_001E": "pop_25_plus",
            "B01003_001E": "total_population",
            "B25003_001E": "total_occupied_units",
            "NAME": "tract_name",
            "state": "state_fips",
            "county": "county_fips",
            "tract": "tract_fips",
        }

        census_df = df.rename(columns=column_mapping)

        # Create tract identifier
        if all(
            col in census_df.columns
            for col in ["state_fips", "county_fips", "tract_fips"]
        ):
            census_df["tract_id"] = (
                census_df["state_fips"].astype(str).str.zfill(2)
                + census_df["county_fips"].astype(str).str.zfill(3)
                + census_df["tract_fips"].astype(str).str.zfill(6)
            )

        # Filter out tracts with missing key data
        initial_count = len(census_df)
        census_df = census_df.dropna(subset=["total_population", "median_income"])
        logger.info(
            "Removed %d tracts with missing key data", initial_count - len(census_df)
        )

        return census_df

    def _log_summary_stats(self, df: pd.DataFrame) -> None:
        """Log summary statistics of the census data."""
        logger.info("Census Data Summary:")
        logger.info("  Total tracts: %d", len(df))

        if "total_population" in df.columns:
            total_pop = df["total_population"].sum()
            avg_pop = df["total_population"].mean()
            logger.info("  Total population: %d", int(total_pop))
            logger.info("  Average population per tract: %.0f", avg_pop)

    def _create_demo_data(self) -> dict[str, Any]:
        """Create demo census data for testing without API key."""
        # Create sample data for Chicago area tracts
        demo_data = {
            "tract_id": [
                "17031000100",
                "17031000200",
                "17031000300",
                "17031000400",
                "17031000500",
                "17031000600",
                "17031000700",
                "17031000800",
                "17031000900",
                "17031001000",
            ],
            "tract_name": [
                "Census Tract 1, Cook County, Illinois",
                "Census Tract 2, Cook County, Illinois",
                "Census Tract 3, Cook County, Illinois",
                "Census Tract 4, Cook County, Illinois",
                "Census Tract 5, Cook County, Illinois",
                "Census Tract 6, Cook County, Illinois",
                "Census Tract 7, Cook County, Illinois",
                "Census Tract 8, Cook County, Illinois",
                "Census Tract 9, Cook County, Illinois",
                "Census Tract 10, Cook County, Illinois",
            ],
            "total_population": [
                2500,
                3200,
                1800,
                4100,
                2900,
                3600,
                2200,
                3800,
                3100,
                2700,
            ],
            "median_income": [
                45000,
                65000,
                38000,
                72000,
                52000,
                68000,
                42000,
                75000,
                58000,
                48000,
            ],
            "median_house_value": [
                280000,
                420000,
                220000,
                480000,
                320000,
                450000,
                250000,
                520000,
                380000,
                300000,
            ],
            "median_age": [35.2, 42.1, 28.5, 45.3, 38.7, 43.2, 31.8, 46.1, 40.2, 36.9],
            "pct_bachelor": [
                25.3,
                45.2,
                18.7,
                52.1,
                38.9,
                47.6,
                22.4,
                54.3,
                42.1,
                29.8,
            ],
            "pct_rented": [45.2, 32.1, 58.3, 28.7, 38.9, 35.4, 62.1, 41.2, 33.8, 49.5],
            # Housing occupancy (ACS B25003); required for TreatmentThresholdProcessor
            "total_occupied_units": [
                2000,
                2560,
                1440,
                3280,
                2320,
                2880,
                1760,
                3040,
                2480,
                2160,
            ],
            "state_fips": ["17"] * 10,
            "county_fips": ["031"] * 10,
            "tract_fips": [f"{i:06d}" for i in range(1, 11)],
        }

        demo_df = pd.DataFrame(demo_data)
        logger.info("Created demo data with %d census tracts", len(demo_df))

        return {"census_data": demo_df}
