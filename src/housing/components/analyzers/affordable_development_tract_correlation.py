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


class AffordableCorrelationAnalyzer(Analyzer):
    """Analyze correlations between the tract-level data for affordable developments,
    
    STR restrictions, and Airbnb listings
    """

    def __init__(self) -> None:
        """Initialize the correlation analyzer."""
        super().__init__(
            "correlation_analysis", "Analyze correlations between affordable development and other tract-level data"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform correlation analysis."""
        logger.info("Collecting and merging tract-level data sets...")

        data = context["airbnb_tract_data"].rename(
            {"point_count": "airbnb_count", "point_density": "airbnb_density"}, axis=1)
        data = data.merge(context["affordable_developments_tract_data"].rename(
            {"point_count": "development_count",
            "point_density": "development_density"}, axis=1), on=["tract_geoid", "geometry"])
        data = data.merge(context["str_tract_data"].rename(
            {"point_count": "str_count", 
             "point_density": "str_density"}, axis=1), on=["tract_geoid", "geometry"]) 

        logger.info("Performing correlation analysis...")

        # Calculate area statistics
        # Convert to projected CRS (UTM Zone 16N for Chicago) for accurate area calculations
        data_projected = data.to_crs("EPSG:32616")
        data["area_km2"] = data_projected.geometry.area / 1_000_000  # Convert to km²

        # Prepare numeric columns for analysis
        # Use zip_count if available (from direct zip aggregation), otherwise tract_count (from tract aggregation)

        numeric_cols = [
            "development_density",
            "unit_density",
            "airbnb_density",
            "units_sum",
            "str_density",
            "price_numeric_max",
            "price_numeric_min",
            "price_numeric_median",
            "number_of_units_sum",
            "number_of_units_mean",
            "area_km2",
        ]

        # Remove rows with missing data
        analysis_data = data[numeric_cols].dropna()

        logger.info(
            "Analyzing %d census tracts with complete data", len(analysis_data)
        )

        # Calculate correlation matrix
        correlation_matrix = analysis_data.corr()

        # Key correlations to highlight
        key_correlations = {
            "Affordable Development Unit Density vs. Airbnb Density": correlation_matrix.loc[
                "unit_density", "airbnb_density"
            ],
            "Affordable Development Density vs. Airbnb Density": correlation_matrix.loc[
                "development_density", "airbnb_density"
            ],
            "Affordable Development Unit Density vs. STR Density": correlation_matrix.loc[
                "unit_density", "str_density"
            ],
            "Affordable Development Density vs. STR Density": correlation_matrix.loc[
                "development_density", "str_density"
            ],
        }

        # Statistical summary
        summary_stats = {
            "total_tracts": len(data),
            "tracts_with_developments": len(data.loc[data.development_count > 0]),
            "avg_development_unit_density": analysis_data["unit_density"].mean(),
            "development_unit_density_std": analysis_data["unit_density"].std(),
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
