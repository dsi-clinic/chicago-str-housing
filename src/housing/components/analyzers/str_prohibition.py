"""Short-term rental prohibition density analyzer.

This module analyzes the spatial density of STR prohibitions and their
relationship to rental prices and housing characteristics.
"""

import logging
from typing import Any

import geopandas as gpd
import pandas as pd

from housing.components.utils import calculate_pairwise_correlations
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class STRProhibitionAnalyzer(Analyzer):
    """Analyze STR prohibition density vs rental prices and housing characteristics.

    Performs spatial aggregation and correlation analysis at census tract level.
    """

    def __init__(
        self,
        filter_outliers: bool = True,
        max_units_per_building: int = 500,
        max_units_per_tract: int = 5000,
        winsorize_density: bool = True,
        winsor_quantile: float = 0.99,
    ) -> None:
        """Initialize the STR prohibition analyzer.

        Args:
            filter_outliers: Whether to filter out outlier buildings/tracts
            max_units_per_building: Maximum units per building (default: 500)
            max_units_per_tract: Maximum units per tract (default: 5000)
            winsorize_density: If True, cap STR units density at the given quantile upstream
            winsor_quantile: Quantile for winsorization cap (e.g., 0.99 for 99th percentile)
        """
        super().__init__(
            "str_prohibition_analysis",
            "Analyze STR prohibition density vs rental prices and housing share",
        )
        self.filter_outliers = filter_outliers
        self.max_units_per_building = max_units_per_building
        self.max_units_per_tract = max_units_per_tract
        self.winsorize_density = winsorize_density
        self.winsor_quantile = winsor_quantile

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform STR prohibition density analysis."""
        logger.info("Analyzing STR prohibition density patterns...")

        # Get data from context
        str_data = context["str_prohibition_data"].copy()
        tract_boundaries = context.get("tract_boundaries")

        # Filter outliers if requested
        if self.filter_outliers:
            str_data = self._filter_building_outliers(str_data)

        if tract_boundaries is None:
            logger.warning("No tract boundaries available, skipping spatial join")
            return self._basic_analysis(str_data)

        # Spatial join to census tracts
        logger.info("Joining STR prohibition data to census tracts...")
        str_with_tracts = str_data.sjoin(
            tract_boundaries, how="left", predicate="within"
        )

        # Aggregate by tract
        tract_str = self._aggregate_by_tract(str_with_tracts, tract_boundaries)
        logger.info("Aggregated STR prohibitions to %d tracts", len(tract_str))

        # Filter tract-level outliers if requested
        if self.filter_outliers:
            tract_str = self._filter_tract_outliers(tract_str)

        # Get rental data if available
        tract_rental = context.get("tract_rental_data")
        airbnb_data = context.get("airbnb_tract_data")

        # Combine datasets
        analysis_df = tract_str.copy()

        if tract_rental is not None:
            logger.info("Merging with rental price data...")
            analysis_df = analysis_df.merge(
                tract_rental[
                    [
                        "tract_geoid",
                        "avg_rental_price",
                        "area_weighted_avg_rent",
                        "min_rental_price",
                        "max_rental_price",
                    ]
                ],
                on="tract_geoid",
                how="left",
            )

        if airbnb_data is not None:
            logger.info("Merging with Airbnb data...")
            # The PointsToTractProcessor creates generic column names
            airbnb_columns = ["tract_geoid", "point_count", "point_density"]
            # Add price columns if they exist
            if "price_numeric_mean" in airbnb_data.columns:
                airbnb_columns.extend(
                    [
                        "price_numeric_mean",
                        "price_numeric_median",
                        "price_numeric_min",
                        "price_numeric_max",
                    ]
                )

            analysis_df = analysis_df.merge(
                airbnb_data[airbnb_columns],
                on="tract_geoid",
                how="left",
            )
            # Rename columns for consistency with visualization expectations
            analysis_df = analysis_df.rename(
                columns={
                    "point_count": "airbnb_count",
                    "point_density": "airbnb_density",
                    "price_numeric_mean": "airbnb_price_mean",
                }
            )

        # Upstream winsorization so all downstream visuals use capped density
        if self.winsorize_density and "str_prohibition_density" in analysis_df.columns:
            analysis_df["str_prohibition_density_raw"] = analysis_df[
                "str_prohibition_density"
            ]
            cap = analysis_df["str_prohibition_density"].quantile(self.winsor_quantile)
            analysis_df["str_prohibition_density"] = analysis_df[
                "str_prohibition_density"
            ].clip(upper=cap)

        # Calculate correlations
        correlations = self._calculate_correlations(analysis_df)

        # Summary statistics
        summary = self._generate_summary(analysis_df, str_data)

        logger.info("\nSTR Prohibition Analysis Summary:")
        logger.info(
            "  Total buildings with prohibitions: %d", summary["total_buildings"]
        )
        logger.info("  Total units prohibited: %d", summary["total_units_prohibited"])
        logger.info(
            "  Tracts with prohibitions: %d", summary["tracts_with_prohibitions"]
        )

        if correlations:
            logger.info("\nKey Correlations:")
            for name, corr in correlations.items():
                logger.info("  %s: %.3f", name, corr)

        return {
            "str_tract_analysis": analysis_df,
            "str_correlations": correlations,
            "str_summary": summary,
        }

    def _aggregate_by_tract(
        self,
        str_with_tracts: pd.DataFrame,
        tract_boundaries: gpd.GeoDataFrame | None = None,
    ) -> pd.DataFrame:
        """Aggregate STR prohibition data by census tract."""
        # Group by tract
        tract_groups = str_with_tracts.groupby("tract_geoid")

        # Aggregate statistics
        agg_dict = {
            "application_id": "count",  # Count of buildings
        }

        if "number_of_units" in str_with_tracts.columns:
            agg_dict["number_of_units"] = ["sum", "mean", "median"]

        tract_agg = tract_groups.agg(agg_dict).reset_index()

        # Flatten column names
        tract_agg.columns = [
            "_".join(col).strip("_") if col[1] else col[0]
            for col in tract_agg.columns.to_numpy()
        ]

        # Rename for clarity
        rename_dict = {
            "application_id_count": "str_prohibition_count",
        }

        if "number_of_units_sum" in tract_agg.columns:
            rename_dict["number_of_units_sum"] = "total_units_prohibited"
            rename_dict["number_of_units_mean"] = "avg_units_per_building"
            rename_dict["number_of_units_median"] = "median_units_per_building"

        tract_agg = tract_agg.rename(columns=rename_dict)

        # Calculate STR prohibition density (prohibitions per km²)
        if tract_boundaries is not None:
            # Calculate area if not already present
            if "area_km2" not in tract_boundaries.columns:
                # Convert to projected CRS for accurate area calculation
                tract_boundaries_projected = tract_boundaries.to_crs("EPSG:32616")
                tract_boundaries = tract_boundaries.copy()
                tract_boundaries["area_km2"] = (
                    tract_boundaries_projected.geometry.area / 1_000_000
                )

            # Merge with tract boundaries to get area
            tract_agg = tract_agg.merge(
                tract_boundaries[["tract_geoid", "area_km2"]],
                on="tract_geoid",
                how="left",
            )
            # Calculate STR prohibition density as units per km² (not buildings per km²)
            if "total_units_prohibited" in tract_agg.columns:
                tract_agg["str_prohibition_density"] = (
                    tract_agg["total_units_prohibited"] / tract_agg["area_km2"]
                )
            else:
                # Fallback to building density if units not available
                tract_agg["str_prohibition_density"] = (
                    tract_agg["str_prohibition_count"] / tract_agg["area_km2"]
                )

        return tract_agg

    def _calculate_correlations(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate key correlations between STR prohibitions and other factors."""
        min_sample_size = 10  # Minimum samples needed for correlation

        # Define correlation pairs - use density metrics for better normalization
        pairs = [
            (
                "str_prohibition_density",
                "avg_rental_price",
                "STR Units Density vs Rental Price",
            ),
            (
                "total_units_prohibited",
                "avg_rental_price",
                "Prohibited Units vs Rental Price",
            ),
            (
                "str_prohibition_density",
                "airbnb_density",
                "STR Units Density vs Airbnb Units Density",
            ),
        ]

        return calculate_pairwise_correlations(df, pairs, min_sample_size)

    def _generate_summary(
        self, analysis_df: pd.DataFrame, str_data: pd.DataFrame
    ) -> dict[str, Any]:
        """Generate summary statistics."""
        summary = {
            "total_buildings": len(str_data),
            "tracts_with_prohibitions": (
                analysis_df["str_prohibition_count"] > 0
            ).sum(),
            "total_tracts_analyzed": len(analysis_df),
        }

        if "total_units_prohibited" in analysis_df.columns:
            summary["total_units_prohibited"] = int(
                analysis_df["total_units_prohibited"].sum()
            )
            summary["avg_units_per_tract"] = float(
                analysis_df["total_units_prohibited"].mean()
            )

        if "avg_rental_price" in analysis_df.columns:
            # Compare rental prices in tracts with vs without prohibitions
            with_prohibitions = analysis_df[analysis_df["str_prohibition_count"] > 0][
                "avg_rental_price"
            ].dropna()

            without_prohibitions = analysis_df[
                analysis_df["str_prohibition_count"] == 0
            ]["avg_rental_price"].dropna()

            if len(with_prohibitions) > 0 and len(without_prohibitions) > 0:
                summary["avg_rent_with_prohibitions"] = float(with_prohibitions.mean())
                summary["avg_rent_without_prohibitions"] = float(
                    without_prohibitions.mean()
                )
                summary["rent_difference"] = float(
                    with_prohibitions.mean() - without_prohibitions.mean()
                )

        return summary

    def _filter_building_outliers(self, str_data: pd.DataFrame) -> pd.DataFrame:
        """Filter out buildings with suspiciously high unit counts.

        Args:
            str_data: STR prohibition data

        Returns:
            Filtered data
        """
        initial_count = len(str_data)
        initial_units = str_data["number_of_units"].sum()

        # Filter buildings with too many units
        filtered = str_data[
            str_data["number_of_units"] <= self.max_units_per_building
        ].copy()

        removed = initial_count - len(filtered)
        removed_units = initial_units - filtered["number_of_units"].sum()

        if removed > 0:
            logger.info(
                "Filtered %d buildings with >%d units (outliers)",
                removed,
                self.max_units_per_building,
            )
            logger.info("  Removed %d units from analysis", removed_units)
            logger.info(
                "  Remaining: %d buildings, %d units",
                len(filtered),
                filtered["number_of_units"].sum(),
            )

        return filtered

    def _filter_tract_outliers(self, tract_data: pd.DataFrame) -> pd.DataFrame:
        """Filter out tracts with suspiciously high unit counts.

        Args:
            tract_data: Aggregated tract-level data

        Returns:
            Filtered data
        """
        if "total_units_prohibited" not in tract_data.columns:
            return tract_data

        initial_count = len(tract_data)

        # Filter tracts with too many units
        filtered = tract_data[
            tract_data["total_units_prohibited"] <= self.max_units_per_tract
        ].copy()

        removed = initial_count - len(filtered)

        if removed > 0:
            logger.info(
                "Filtered %d tracts with >%d units (outliers)",
                removed,
                self.max_units_per_tract,
            )
            logger.info("  Remaining: %d tracts", len(filtered))

        return filtered

    def _basic_analysis(self, str_data: pd.DataFrame) -> dict[str, Any]:
        """Perform basic analysis without spatial aggregation."""
        logger.info("Performing basic analysis without tract boundaries...")

        summary = {
            "total_buildings": len(str_data),
        }

        if "number_of_units" in str_data.columns:
            summary["total_units_prohibited"] = int(str_data["number_of_units"].sum())
            summary["avg_units_per_building"] = float(
                str_data["number_of_units"].mean()
            )

        return {
            "str_tract_analysis": None,
            "str_correlations": {},
            "str_summary": summary,
        }
