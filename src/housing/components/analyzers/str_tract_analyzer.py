"""Census tract-level analyzer.

This module performs statistical analysis on tract-level rental data.
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


class STRTractAnalyzer(Analyzer):
    """Analyze census tract-level rental data.

    This demonstrates analysis at a more granular level than community areas.
    Tracts are smaller, so we can detect more localized patterns.
    """

    def __init__(self) -> None:
        """Initialize the tract analyzer."""
        super().__init__(
            "str_tract_analysis", "Analyze correlations in census tract STR data"
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform tract-level analysis on STR data."""
        logger.info("Performing correlation analysis on tract rental data...")

        data = context["str_tract_data"]

        # Calculate area statistics
        # Convert to projected CRS (UTM Zone 16N for Chicago) for accurate area calculations
        data_projected = data.to_crs("EPSG:32616")
        data["area_km2"] = data_projected.geometry.area / 1_000_000  # Convert to km²

        # Prepare numeric columns for analysis
        numeric_cols = ["point_count", "point_density", "area_km2"]

        # Remove rows with missing data
        analysis_data = data[numeric_cols].dropna()

        logger.info("Analyzing %d census tracts with complete data", len(analysis_data))

        # Calculate correlation matrix
        correlation_matrix = analysis_data.corr()

        key_correlations = {
            "point_count vs point_density": correlation_matrix.loc[
                "point_count", "point_density"
            ],
            "area_km2 vs point_density": correlation_matrix.loc[
                "area_km2", "point_density"
            ],
            "area_km2 vs point_count": correlation_matrix.loc[
                "area_km2", "point_count"
            ],
        }

        # Statistical summary
        summary_stats = {
            "total_tracts": len(data),
            "tracts_with_data": len(analysis_data),
            "mean_point_count": analysis_data["point_count"].mean(),
            "median_point_count": analysis_data["point_count"].median(),
            "std_point_count": analysis_data["point_count"].std(),
            "mean_point_density": analysis_data["point_density"].mean(),
            "median_point_density": analysis_data["point_density"].median(),
            "std_point_density": analysis_data["point_density"].std(),
            "tracts_with_zero_STRs": (data["point_count"] == 0).sum(),
            "top_10pct_density_threshold": analysis_data["point_density"].quantile(0.9),
            "skew_point_density": analysis_data["point_density"].skew(),
            "kurtosis_point_density": analysis_data["point_density"].kurtosis(),
        }

        logger.info("Key Correlations Found:")
        for name, corr in key_correlations.items():
            strength = self._get_correlation_strength(abs(corr))
            logger.info("  %s: %.3f (%s)", name, corr, strength)

        #  Gini coefficient for STR count... is this helpful?
        def gini_coefficient(values):
            values = np.sort(values)
            n = len(values)
            if n == 0:
                return np.nan
            index = np.arange(1, n + 1)
            return (2 * np.sum(index * values)) / (n * np.sum(values)) - (n + 1) / n

        gini = gini_coefficient(analysis_data["point_count"].values)
        summary_stats["gini_point_count"] = gini
        logger.info("Computed Gini coefficient: %.3f", gini)

        # Top 5 tracts by STR density
        top5 = analysis_data.nlargest(5, "point_density")[
            ["point_count", "point_density"]
        ]

        logger.info("Top 5 tracts by STR density:\n%s", top5.to_string())

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
