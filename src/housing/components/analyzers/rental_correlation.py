"""Rental correlation analysis component.

This module performs correlation analysis specifically on rental data at different
geographic levels (tract and community area). This is a specialized analyzer
for rental price data - students should create their own analyzers for other data types.
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


class RentalCorrelationAnalyzer(Analyzer):
    """Analyze correlations in rental data at community level.

    This demonstrates how to perform statistical analysis on rental data.
    Students should create their own analyzers for other data types (crime, housing violations, etc.).
    """

    def __init__(self) -> None:
        """Initialize the rental correlation analyzer."""
        super().__init__(
            "rental_correlation_analysis",
            "Analyze correlations in community rental data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform correlation analysis."""
        logger.info("Performing correlation analysis on community rental data...")

        data = context["community_rental_data"]

        # Calculate area statistics
        # Convert to projected CRS (UTM Zone 16N for Chicago) for accurate area calculations
        data_projected = data.to_crs("EPSG:32616")
        data["area_km2"] = data_projected.geometry.area / 1_000_000  # Convert to km²

        # Prepare numeric columns for analysis
        # Use zip_count if available (from direct zip aggregation), otherwise tract_count (from tract aggregation)
        count_col = "zip_count" if "zip_count" in data.columns else "tract_count"

        numeric_cols = [
            "area_weighted_avg_rent",
            "avg_rental_price",
            "min_rental_price",
            "max_rental_price",
            count_col,
            "area_km2",
        ]

        # Remove rows with missing data
        analysis_data = data[numeric_cols].dropna()

        logger.info(
            "Analyzing %d community areas with complete data", len(analysis_data)
        )

        # Calculate correlation matrix
        correlation_matrix = analysis_data.corr()

        # Key correlations to highlight
        count_label = "Zip Count" if count_col == "zip_count" else "Tract Count"
        key_correlations = {
            "Area vs Average Rent": correlation_matrix.loc[
                "area_km2", "avg_rental_price"
            ],
            f"Area vs {count_label}": correlation_matrix.loc["area_km2", count_col],
            "Min vs Max Rent": correlation_matrix.loc[
                "min_rental_price", "max_rental_price"
            ],
            "Average vs Area-Weighted Rent": correlation_matrix.loc[
                "avg_rental_price", "area_weighted_avg_rent"
            ],
        }

        # Statistical summary
        summary_stats = {
            "total_communities": len(data),
            "communities_with_data": len(analysis_data),
            "avg_rental_price": analysis_data["avg_rental_price"].mean(),
            "rental_price_std": analysis_data["avg_rental_price"].std(),
            "avg_area_km2": analysis_data["area_km2"].mean(),
            "key_correlations": key_correlations,
        }

        logger.info("Key Correlations Found:")
        for name, corr in key_correlations.items():
            strength = self._get_correlation_strength(abs(corr))
            logger.info("  %s: %.3f (%s)", name, corr, strength)

        return {
            "correlation_matrix": correlation_matrix,
            "analysis_data": analysis_data,
            "summary_stats": summary_stats,
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
