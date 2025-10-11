"""Community-level correlation analyzer.

This module performs statistical correlation analysis on community-level rental data.
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


class CorrelationAnalyzer(Analyzer):
    """Analyze correlations in the merged spatial dataset.

    This demonstrates how to perform statistical analysis on merged spatial data.
    """

    def __init__(self) -> None:
        """Initialize the correlation analyzer."""
        super().__init__(
            "correlation_analysis", "Analyze correlations in community rental data"
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

        logger.info(
            "Analyzing %d community areas with complete data", len(analysis_data)
        )

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
