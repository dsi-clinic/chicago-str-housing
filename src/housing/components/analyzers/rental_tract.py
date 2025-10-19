"""Rental tract-level analyzer.

This module performs statistical analysis specifically on tract-level rental data.
This is a specialized analyzer for rental price data - students should create their
own analyzers for other data types.
"""

import logging
from typing import Any

from housing.components.constants import (
    CORRELATION_MODERATE_THRESHOLD,
    CORRELATION_STRONG_THRESHOLD,
    CORRELATION_WEAK_THRESHOLD,
)
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class RentalTractAnalyzer(Analyzer):
    """Analyze census tract-level rental data.

    This demonstrates analysis at a more granular level than community areas.
    Tracts are smaller, so we can detect more localized patterns.
    Students should create their own analyzers for other data types (crime, housing violations, etc.).
    """

    def __init__(self) -> None:
        """Initialize the rental tract analyzer."""
        super().__init__(
            "rental_tract_analysis", "Analyze correlations in census tract rental data"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform tract-level analysis."""
        logger.info("Performing correlation analysis on tract rental data...")

        data = context["tract_rental_data"]

        # Calculate area statistics
        # Convert to projected CRS (UTM Zone 16N for Chicago) for accurate area calculations
        data_projected = data.to_crs("EPSG:32616")
        data["area_km2"] = data_projected.geometry.area / 1_000_000  # Convert to km²

        # Prepare numeric columns for analysis
        numeric_cols = [
            "area_weighted_avg_rent",
            "avg_rental_price",
            "min_rental_price",
            "max_rental_price",
            "zip_count",
            "area_km2",
        ]

        # Remove rows with missing data
        analysis_data = data[numeric_cols].dropna()

        logger.info("Analyzing %d census tracts with complete data", len(analysis_data))

        # Calculate correlation matrix
        correlation_matrix = analysis_data.corr()

        # Key correlations to highlight
        key_correlations = {
            "Area vs Average Rent": correlation_matrix.loc[
                "area_km2", "avg_rental_price"
            ],
            "Area vs Zip Count": correlation_matrix.loc["area_km2", "zip_count"],
            "Min vs Max Rent": correlation_matrix.loc[
                "min_rental_price", "max_rental_price"
            ],
            "Average vs Area-Weighted Rent": correlation_matrix.loc[
                "avg_rental_price", "area_weighted_avg_rent"
            ],
        }

        # Statistical summary
        summary_stats = {
            "total_tracts": len(data),
            "tracts_with_data": len(analysis_data),
            "avg_rental_price": analysis_data["avg_rental_price"].mean(),
            "rental_price_std": analysis_data["avg_rental_price"].std(),
            "avg_area_km2": analysis_data["area_km2"].mean(),
            "key_correlations": key_correlations,
        }

        logger.info("Key Correlations Found:")
        for name, corr in key_correlations.items():
            strength = self._get_correlation_strength(abs(corr))
            logger.info("  %s: %.3f (%s)", name, corr, strength)

        # Compare with community-level data if available
        if "summary_stats" in context:
            community_stats = context["summary_stats"]
            logger.info("\n=== Tract vs Community Comparison ===")
            logger.info(
                "Average rent - Tract: $%.2f, Community: $%.2f",
                summary_stats["avg_rental_price"],
                community_stats.get("avg_rental_price", 0),
            )
            logger.info(
                "Std dev - Tract: $%.2f, Community: $%.2f",
                summary_stats["rental_price_std"],
                community_stats.get("rental_price_std", 0),
            )

        return {
            "tract_correlation_matrix": correlation_matrix,
            "tract_analysis_data": analysis_data,
            "tract_summary_stats": summary_stats,
        }

    def _get_correlation_strength(self, abs_corr: float) -> str:
        """Classify correlation strength."""
        if abs_corr >= CORRELATION_STRONG_THRESHOLD:
            return "Strong"
        elif abs_corr >= CORRELATION_MODERATE_THRESHOLD:
            return "Moderate"
        elif abs_corr >= CORRELATION_WEAK_THRESHOLD:
            return "Weak"
        else:
            return "Negligible"
