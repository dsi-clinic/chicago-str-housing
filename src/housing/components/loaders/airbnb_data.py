"""Airbnb listings data loader.

This module loads Airbnb listings data with spatial coordinates for
aggregation to census tract level.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class AirbnbDataLoader(DataLoader):
    """Load Airbnb listings data.

    Loads CSV data with listing details including location, pricing,
    and property characteristics. Converts to GeoDataFrame for spatial operations.
    """

    def __init__(
        self,
        file_path: str | None = None,
        remove_outliers: bool = True,
        outlier_method: str = "iqr",
        iqr_multiplier: float = 1.5,
        max_minimum_nights: int = 31,
        filter_inactive: bool = False,
    ) -> None:
        """Initialize the Airbnb data loader.

        Args:
            file_path: Optional path to Airbnb listings file
            remove_outliers: Whether to remove price outliers (default: True)
            outlier_method: Method for outlier detection ('iqr' or 'zscore')
            iqr_multiplier: IQR multiplier for outlier detection (default: 1.5)
            max_minimum_nights: Maximum minimum_nights to include (default: 31)
                                Per Chicago ordinance, STRs are ≤31 days; longer stays are not STRs
            filter_inactive: Whether to filter out listings with 0 reviews (default: False)
        """
        super().__init__(
            "airbnb_data",
            file_path or "/project/data/listings.csv",
            "Load Airbnb listings data",
        )
        self.remove_outliers = remove_outliers
        self.outlier_method = outlier_method
        self.iqr_multiplier = iqr_multiplier
        self.max_minimum_nights = max_minimum_nights
        self.filter_inactive = filter_inactive

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and clean Airbnb data."""
        logger.info("Loading Airbnb data from: %s", self.file_path)

        # Load the CSV data
        listings_df = pd.read_csv(self.file_path)

        # Clean price column (remove $ and commas, convert to float)
        if "price" in listings_df.columns:
            listings_df["price_numeric"] = (
                listings_df["price"]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.replace(",", "", regex=False)
                .astype(float)
            )

        # Keep relevant columns
        columns_to_keep = [
            "id",
            "latitude",
            "longitude",
            "price_numeric",
            "room_type",
            "property_type",
            "accommodates",
            "bedrooms",
            "beds",
            "number_of_reviews",
            "review_scores_rating",
            "neighbourhood_cleansed",
            "minimum_nights",
        ]

        # Only keep columns that exist
        columns_to_keep = [col for col in columns_to_keep if col in listings_df.columns]
        listings_clean = listings_df[columns_to_keep].copy()

        # Drop rows with missing lat/lon
        listings_clean = listings_clean.dropna(subset=["latitude", "longitude"])

        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(
            listings_clean,
            geometry=gpd.points_from_xy(
                listings_clean.longitude, listings_clean.latitude
            ),
            crs="EPSG:4326",
        )

        logger.info("Loaded %d Airbnb listings", len(gdf))
        logger.info(
            "Price range: $%.2f - $%.2f",
            gdf["price_numeric"].min(),
            gdf["price_numeric"].max(),
        )
        logger.info("Room types: %s", gdf["room_type"].unique().tolist())

        # Filter extended-stay/monthly rentals
        gdf = self._filter_extended_stay(gdf)

        # Filter inactive listings if requested
        if self.filter_inactive:
            gdf = self._filter_inactive_listings(gdf)

        # Remove outliers if requested
        if self.remove_outliers:
            gdf = self._remove_outliers(gdf)

        return {"airbnb_data": gdf}

    def _filter_extended_stay(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Filter out extended-stay/monthly rental listings.

        Listings with minimum_nights > max_minimum_nights are typically
        corporate housing or monthly rentals, not traditional short-term rentals.

        Args:
            gdf: GeoDataFrame with minimum_nights column

        Returns:
            GeoDataFrame with extended-stay listings removed
        """
        if "minimum_nights" not in gdf.columns:
            logger.warning(
                "minimum_nights column not found, skipping extended-stay filter"
            )
            return gdf

        initial_count = len(gdf)

        # Filter out extended-stay listings
        extended_stay = gdf[gdf["minimum_nights"] > self.max_minimum_nights]
        gdf_filtered = gdf[gdf["minimum_nights"] <= self.max_minimum_nights].copy()

        if len(extended_stay) > 0:
            logger.info(
                "Extended-stay filter (minimum_nights > %d):", self.max_minimum_nights
            )
            logger.info(
                "  Removed %d extended-stay listings (%.1f%% of data)",
                len(extended_stay),
                100 * len(extended_stay) / initial_count,
            )

            # Log some examples
            max_examples = 5
            if len(extended_stay) <= max_examples:
                for _, row in extended_stay.iterrows():
                    logger.info(
                        "    Listing %s: %d nights minimum, $%.2f/night",
                        row["id"],
                        row["minimum_nights"],
                        row["price_numeric"],
                    )
            else:
                logger.info(
                    "    Example: %d to %d nights minimum",
                    extended_stay["minimum_nights"].min(),
                    extended_stay["minimum_nights"].max(),
                )

            logger.info("  After filtering: %d listings", len(gdf_filtered))
        else:
            logger.info(
                "  No extended-stay listings found (minimum_nights > %d)",
                self.max_minimum_nights,
            )

        return gdf_filtered

    def _filter_inactive_listings(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Filter out listings with zero reviews (potentially inactive).

        Args:
            gdf: GeoDataFrame with number_of_reviews column

        Returns:
            GeoDataFrame with inactive listings removed
        """
        if "number_of_reviews" not in gdf.columns:
            logger.warning(
                "number_of_reviews column not found, skipping inactive filter"
            )
            return gdf

        initial_count = len(gdf)

        # Filter out listings with 0 reviews
        inactive = gdf[gdf["number_of_reviews"] == 0]
        gdf_filtered = gdf[gdf["number_of_reviews"] > 0].copy()

        if len(inactive) > 0:
            logger.info("Inactive listing filter (0 reviews):")
            logger.info(
                "  Removed %d listings with 0 reviews (%.1f%% of data)",
                len(inactive),
                100 * len(inactive) / initial_count,
            )
            logger.info("  After filtering: %d listings", len(gdf_filtered))
        else:
            logger.info("  No inactive listings found (all have >0 reviews)")

        return gdf_filtered

    def _remove_outliers(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Remove outliers from Airbnb price data.

        Args:
            gdf: GeoDataFrame with price_numeric column

        Returns:
            GeoDataFrame with outliers removed
        """
        initial_count = len(gdf)
        prices = gdf["price_numeric"]

        if self.outlier_method == "iqr":
            # IQR method (more robust than z-score)
            q1 = prices.quantile(0.25)
            q3 = prices.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - (self.iqr_multiplier * iqr)
            upper_bound = q3 + (self.iqr_multiplier * iqr)

            outliers = gdf[(prices < lower_bound) | (prices > upper_bound)]
            gdf_clean = gdf[(prices >= lower_bound) & (prices <= upper_bound)].copy()

            logger.info("Outlier detection using IQR method:")
            logger.info("  Q1: $%.2f, Q3: $%.2f, IQR: $%.2f", q1, q3, iqr)
            logger.info("  Bounds: $%.2f - $%.2f", lower_bound, upper_bound)

        elif self.outlier_method == "zscore":
            # Z-score method (assumes normal distribution)
            z_score_threshold = 3.0  # Standard threshold for outlier detection
            mean = prices.mean()
            std = prices.std()
            z_scores = (prices - mean).abs() / std
            outliers = gdf[z_scores > z_score_threshold]
            gdf_clean = gdf[z_scores <= z_score_threshold].copy()

            logger.info(
                "Outlier detection using Z-score method (>%.0f std):", z_score_threshold
            )
            logger.info("  Mean: $%.2f, Std: $%.2f", mean, std)

        else:
            logger.warning(
                "Unknown outlier method: %s. Skipping outlier removal.",
                self.outlier_method,
            )
            return gdf

        if len(outliers) > 0:
            logger.info(
                "  Removed %d outliers (%.1f%% of data):",
                len(outliers),
                100 * len(outliers) / initial_count,
            )
            # Log only the most extreme outliers (top 5)
            extreme_outliers = outliers.nlargest(min(5, len(outliers)), "price_numeric")
            for _, row in extreme_outliers.iterrows():
                logger.info(
                    "    Listing %s: $%.2f (%s)",
                    row["id"],
                    row["price_numeric"],
                    row.get("room_type", "unknown"),
                )

            logger.info("  After outlier removal: %d listings", len(gdf_clean))
            logger.info(
                "  New price range: $%.2f - $%.2f",
                gdf_clean["price_numeric"].min(),
                gdf_clean["price_numeric"].max(),
            )
        else:
            logger.info("  No outliers detected.")
            gdf_clean = gdf

        return gdf_clean
