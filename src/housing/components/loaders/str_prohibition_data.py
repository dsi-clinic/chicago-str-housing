"""Chicago short-term rental prohibition data loader.

This module loads data from the City of Chicago API about buildings where
short-term rentals are prohibited.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd
import requests

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class STRProhibitionDataLoader(DataLoader):
    """Load Chicago short-term rental prohibition data.

    Loads data from City of Chicago API endpoint about buildings with STR prohibitions.
    Converts to GeoDataFrame for spatial analysis.
    """

    def __init__(
        self,
        api_url: str = "https://data.cityofchicago.org/resource/7bzs-jsyj.json",
        limit: int = 10000,
        deduplicate_coords: bool = False,
        coord_precision: int = 5,
    ) -> None:
        """Initialize the STR prohibition data loader.

        Args:
            api_url: City of Chicago API endpoint URL
            limit: Maximum number of records to fetch (default: 10000)
            deduplicate_coords: Remove entries at same coordinates (default: False)
            coord_precision: Decimal places for coordinate rounding (default: 5 ~1m)
        """
        super().__init__(
            "str_prohibition_data",
            api_url,
            "Load Chicago STR prohibition data from API",
        )
        self.api_url = api_url  # Store URL separately to avoid Path() mangling
        self.limit = limit
        self.deduplicate_coords = deduplicate_coords
        self.coord_precision = coord_precision

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load STR prohibition data from Chicago Open Data API."""
        logger.info("Fetching STR prohibition data from: %s", self.api_url)

        try:
            # Fetch data from API with pagination
            params = {"$limit": self.limit}
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            str_df = pd.DataFrame(data)

            logger.info("Fetched %d STR prohibition records", len(str_df))

        except Exception as e:
            logger.error("Failed to fetch STR prohibition data: %s", e)
            raise

        # Parse numeric fields
        if "number_of_units" in str_df.columns:
            str_df["number_of_units"] = pd.to_numeric(
                str_df["number_of_units"], errors="coerce"
            )

        if "latitude" in str_df.columns and "longitude" in str_df.columns:
            str_df["latitude"] = pd.to_numeric(str_df["latitude"], errors="coerce")
            str_df["longitude"] = pd.to_numeric(str_df["longitude"], errors="coerce")

        # Parse dates
        date_columns = ["recorded_date", "signed_date", "vote_date"]
        for col in date_columns:
            if col in str_df.columns:
                str_df[col] = pd.to_datetime(str_df[col], errors="coerce")

        # Fix data quality issue: signed_date before 2015 is erroneous
        # The STR prohibition program started in late 2015
        # Set any signed_date before 2015 to the minimum valid date (2015-10-25)
        if "signed_date" in str_df.columns:
            min_valid_date = pd.Timestamp("2015-10-25")
            erroneous_count = (str_df["signed_date"] < min_valid_date).sum()
            if erroneous_count > 0:
                logger.warning(
                    "Found %d records with signed_date before 2015, setting to %s",
                    erroneous_count,
                    min_valid_date.strftime("%Y-%m-%d"),
                )
                str_df.loc[str_df["signed_date"] < min_valid_date, "signed_date"] = (
                    min_valid_date
                )

        # Note: recorded_date is when condo declaration was recorded (can be 1950s+)
        # signed_date is when STR prohibition was signed (typically 2016+)
        # For temporal analysis, signed_date is more relevant
        if "signed_date" in str_df.columns and "recorded_date" in str_df.columns:
            # Use signed_date as primary date for STR prohibition timing
            str_df["prohibition_date"] = str_df["signed_date"].fillna(
                str_df["recorded_date"]
            )
            logger.info(
                "Created prohibition_date field (using signed_date when available)"
            )

        # Drop rows without valid coordinates
        initial_count = len(str_df)
        str_df = str_df.dropna(subset=["latitude", "longitude"])
        logger.info(
            "Dropped %d records without valid coordinates", initial_count - len(str_df)
        )

        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(
            str_df,
            geometry=gpd.points_from_xy(str_df.longitude, str_df.latitude),
            crs="EPSG:4326",
        )

        # Deduplicate by coordinates if requested
        if self.deduplicate_coords:
            gdf = self._deduplicate_by_coordinates(gdf)

        # Log summary statistics
        logger.info("STR Prohibition Data Summary:")
        logger.info("  Total buildings: %d", len(gdf))

        if "number_of_units" in gdf.columns:
            total_units = gdf["number_of_units"].sum()
            avg_units = gdf["number_of_units"].mean()
            logger.info("  Total units prohibited: %d", int(total_units))
            logger.info("  Average units per building: %.1f", avg_units)

        if "recorded_date" in gdf.columns:
            date_range = gdf["recorded_date"].dropna()
            if len(date_range) > 0:
                logger.info(
                    "  Date range: %s to %s",
                    date_range.min().strftime("%Y-%m-%d"),
                    date_range.max().strftime("%Y-%m-%d"),
                )

        # Get unique applicant roles
        if "applicant_role" in gdf.columns:
            roles = gdf["applicant_role"].value_counts()
            logger.info("  Top applicant roles:")
            for role, count in roles.head(5).items():
                logger.info("    %s: %d", role, count)

        return {"str_prohibition_data": gdf}

    def _deduplicate_by_coordinates(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Remove duplicate entries at the same coordinates.

        Keeps the most recent entry (by recorded_date) for each location.

        Args:
            gdf: GeoDataFrame with STR prohibition data

        Returns:
            Deduplicated GeoDataFrame
        """
        initial_count = len(gdf)

        # Round coordinates to specified precision
        gdf["lat_round"] = gdf["latitude"].round(self.coord_precision)
        gdf["lon_round"] = gdf["longitude"].round(self.coord_precision)

        # Sort by recorded_date (most recent first)
        if "recorded_date" in gdf.columns:
            gdf_sorted = gdf.sort_values(
                "recorded_date", ascending=False, na_position="last"
            )
        else:
            gdf_sorted = gdf.copy()

        # Keep first (most recent) entry for each coordinate
        gdf_dedup = gdf_sorted.drop_duplicates(
            subset=["lat_round", "lon_round"], keep="first"
        ).copy()

        # Drop temporary columns
        gdf_dedup = gdf_dedup.drop(columns=["lat_round", "lon_round"])

        removed = initial_count - len(gdf_dedup)
        if removed > 0:
            logger.info(
                "Deduplicated %d entries at same coordinates (kept most recent)",
                removed,
            )
            logger.info("  Remaining: %d unique locations", len(gdf_dedup))

        return gdf_dedup
