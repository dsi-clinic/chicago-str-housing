"""Census tract-level analyzer.

This module performs statistical analysis on tract-level STR building data.
"""

import logging
from typing import Any

import numpy as np

from housing.components.constants import (
    CORRELATION_MODERATE_THRESHOLD,
    CORRELATION_STRONG_THRESHOLD,
    CORRELATION_WEAK_THRESHOLD,
)
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class STRBuildingsTractAnalyzer(Analyzer):
    """Analyze census tract-level STR building data.

    This demonstrates analysis at a more granular level than community areas.
    Tracts are smaller, so we can detect more localized patterns.
    """

    def __init__(self) -> None:
        """Initialize the tract analyzer."""
        super().__init__(
            "str_tract_analysis",
            "Analyze correlations in census tract STR building data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform tract-level analysis on STR building data."""
        logger.info("Performing correlation analysis on tract STR building data...")

        data = context["str_buildings_tract_data"]

        # Calculate area statistics
        # Convert to projected CRS (UTM Zone 16N for Chicago) for accurate area calculations
        data_projected = data.to_crs("EPSG:32616")
        data["area_km2"] = data_projected.geometry.area / 1_000_000  # Convert to km²

        # Prepare numeric columns for analysis
        numeric_cols = ["str_buildings_count", "str_buildings_density", "area_km2"]

        # Remove rows with missing data
        analysis_data = data[numeric_cols].dropna()

        logger.info("Analyzing %d census tracts with complete data", len(analysis_data))

        # Calculate correlation matrix
        correlation_matrix = analysis_data.corr()

        key_correlations = {
            "str_buildings_count vs str_buildings_density": correlation_matrix.loc[
                "str_buildings_count", "str_buildings_density"
            ],
            "area_km2 vs str_buildings_density": correlation_matrix.loc[
                "area_km2", "str_buildings_density"
            ],
            "area_km2 vs str_buildings_count": correlation_matrix.loc[
                "area_km2", "str_buildings_count"
            ],
        }

        # Statistical summary
        summary_stats = {
            "total_tracts": len(data),
            "tracts_with_data": len(analysis_data),
            "mean_point_count": analysis_data["str_buildings_count"].mean(),
            "median_point_count": analysis_data["str_buildings_count"].median(),
            "std_point_count": analysis_data["str_buildings_count"].std(),
            "mean_point_density": analysis_data["str_buildings_count"].mean(),
            "median_point_density": analysis_data["str_buildings_count"].median(),
            "std_point_density": analysis_data["str_buildings_count"].std(),
            "tracts_with_zero_STRs": (data["str_buildings_count"] == 0).sum(),
            "top_10pct_density_threshold": analysis_data[
                "str_buildings_density"
            ].quantile(0.9),
            "skew_point_density": analysis_data["str_buildings_density"].skew(),
            "kurtosis_point_density": analysis_data["str_buildings_density"].kurtosis(),
        }

        logger.info("Key Correlations Found:")
        for name, corr in key_correlations.items():
            strength = self._get_correlation_strength(abs(corr))
            logger.info("  %s: %.3f (%s)", name, corr, strength)

        #  Computing Gini coefficient for STR building count
        def gini_coefficient(values: np.ndarray) -> float:
            values = np.sort(values)
            n = len(values)
            if n == 0:
                return np.nan
            index = np.arange(1, n + 1)
            return (2 * np.sum(index * values)) / (n * np.sum(values)) - (n + 1) / n

        gini = gini_coefficient(analysis_data["str_buildings_count"].values)
        summary_stats["gini_point_count"] = gini
        logger.info("Computed Gini coefficient: %.3f", gini)

        # Top 5 tracts by STR building density
        top5 = analysis_data.nlargest(5, "str_buildings_density")[
            ["str_buildings_count", "str_buildings_density"]
        ]

        logger.info("Top 5 tracts by STR building density:\n%s", top5.to_string())

        return {
            "str_tract_correlation_matrix": correlation_matrix,
            "str_tract_summary_stats": summary_stats,
            "str_tract_key_correlations": key_correlations,
            "str_tract_top5_density": top5,
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
