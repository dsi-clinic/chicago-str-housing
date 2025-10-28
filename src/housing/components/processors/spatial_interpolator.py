"""Spatial Data Interpolator using KNN for Missing Values.

This processor fills missing values using K-nearest neighbors
based on spatial proximity and similar characteristics.
Handles census data, rental prices, and other spatial variables.
"""

import logging
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)

# Constants
MIN_DATA_COVERAGE_THRESHOLD = 0.5  # Minimum fraction of non-missing data required


class SpatialInterpolator(DataProcessor):
    """Interpolates missing values using spatial KNN."""

    def __init__(
        self, k_neighbors: int = 5, interpolation_columns: list[str] | None = None
    ) -> None:
        """Initialize the interpolator.

        Args:
            k_neighbors: Number of neighbors to use for interpolation
            interpolation_columns: List of columns to interpolate. If None, auto-detect clustering variables.
        """
        self.k_neighbors = k_neighbors
        self.interpolation_columns = interpolation_columns

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Interpolate missing values in the merged tract data."""
        logger.info("Starting spatial interpolation using KNN (k=%d)", self.k_neighbors)

        if "merged_tract_data" not in context:
            logger.warning("No merged tract data found, skipping interpolation")
            return context

        gdf = context["merged_tract_data"].copy()

        # Determine which columns to interpolate
        if self.interpolation_columns is None:
            # Auto-detect clustering variables that need interpolation
            clustering_variables = [
                # Census demographics
                "census_median_income",
                "census_median_house_value",
                "census_median_age",
                "census_pct_bachelor",
                "census_pct_rented",
                "census_population",
                # Housing market
                "rental_price_mean",
                "airbnb_price_mean",
                # Population
                "population_density",
            ]
            # Only interpolate variables that exist and have missing data
            interpolation_cols = []
            for col in clustering_variables:
                if col in gdf.columns and gdf[col].isna().any():
                    interpolation_cols.append(col)
        else:
            interpolation_cols = [
                col for col in self.interpolation_columns if col in gdf.columns
            ]

        if not interpolation_cols:
            logger.info("No columns need interpolation")
            context["merged_tract_data"] = gdf
            return context

        logger.info(
            "Interpolating %d variables with missing data", len(interpolation_cols)
        )

        # Interpolate each variable
        for col in interpolation_cols:
            gdf[col] = self._interpolate_variable(gdf, col, interpolation_cols)

        # Log results
        total_remaining = sum(gdf[col].isna().sum() for col in interpolation_cols)
        logger.info(
            "Interpolation complete: %d values still missing across all variables",
            total_remaining,
        )

        context["merged_tract_data"] = gdf
        return context

    def _interpolate_variable(
        self, gdf: gpd.GeoDataFrame, target_col: str, all_interpolation_cols: list[str]
    ) -> pd.Series:
        """Interpolate missing values for a single variable using spatial KNN."""
        # Get tract centroids in projected coordinates for accurate distance calculation
        centroids_projected = gdf.geometry.to_crs(
            "EPSG:5070"
        ).centroid  # Albers Equal Area
        coords = np.column_stack([centroids_projected.x, centroids_projected.y])

        # Identify tracts with missing values for this variable
        missing_mask = gdf[target_col].isna()
        valid_mask = ~missing_mask

        if missing_mask.sum() == 0:
            return gdf[target_col]

        if valid_mask.sum() < self.k_neighbors:
            logger.warning(
                "Not enough valid values (%d) for KNN interpolation of %s",
                valid_mask.sum(),
                target_col,
            )
            return gdf[target_col]

        # Prepare features for KNN
        X_train = coords[valid_mask]
        y_train = gdf.loc[valid_mask, target_col]
        X_predict = coords[missing_mask]

        # Add other variables as features if they have sufficient coverage
        other_interpolation_cols = [
            col for col in all_interpolation_cols if col != target_col
        ]
        features = [coords]

        # Add other variables as features if they have sufficient coverage
        for col in other_interpolation_cols:
            col_data = gdf[col]
            # Only use columns with < 50% missing data
            if col_data.notna().sum() / len(col_data) > MIN_DATA_COVERAGE_THRESHOLD:
                # Fill remaining NaN with median for feature calculation
                col_filled = col_data.fillna(col_data.median())
                features.append(col_filled.to_numpy().reshape(-1, 1))

        # Combine all features
        if len(features) > 1:
            feature_matrix = np.hstack(features)
        else:
            feature_matrix = coords

        # Standardize features
        scaler = StandardScaler()
        feature_matrix_scaled = scaler.fit_transform(feature_matrix)

        # Prepare training and prediction data
        X_train = feature_matrix_scaled[valid_mask]
        X_predict = feature_matrix_scaled[missing_mask]

        # Fit KNN model
        knn = NearestNeighbors(n_neighbors=self.k_neighbors, metric="euclidean")
        knn.fit(X_train)

        # Find neighbors
        distances, neighbor_indices = knn.kneighbors(X_predict)

        # Interpolate using inverse distance weighting
        interpolated_values = []

        for _, (dists, indices) in enumerate(zip(distances, neighbor_indices)):
            neighbor_values = y_train.iloc[indices]

            # Use inverse distance weighting (avoid division by zero)
            weights = 1.0 / (dists + 1e-10)  # Add small epsilon
            weights = weights / weights.sum()  # Normalize

            # Calculate weighted average
            interpolated_value = np.sum(neighbor_values * weights)
            interpolated_values.append(interpolated_value)

        # Create result series
        result = gdf[target_col].copy()
        result.iloc[missing_mask] = interpolated_values

        return result


def create_interpolator(
    k_neighbors: int = 5, columns: list[str] | None = None
) -> SpatialInterpolator:
    """Factory function to create a spatial interpolator.

    Args:
        k_neighbors: Number of neighbors for KNN interpolation
        columns: Specific columns to interpolate (None for auto-detection)

    Returns:
        Configured SpatialInterpolator instance
    """
    return SpatialInterpolator(k_neighbors=k_neighbors, interpolation_columns=columns)
