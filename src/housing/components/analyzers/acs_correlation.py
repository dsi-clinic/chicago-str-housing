"""ACS ensus tract-level analyzer.

This module performs statistical analysis on tract-level ACS data.
"""

import logging
from itertools import combinations
from typing import Any

from housing.components.constants import (
    CORRELATION_MODERATE_THRESHOLD,
    CORRELATION_STRONG_THRESHOLD,
    CORRELATION_WEAK_THRESHOLD,
)
from pipeline.base import Analyzer

logger = logging.getLogger(__name__)


class ACSTractAnalyzer(Analyzer):
    """Analyze census tract-level acs demographic data.

    This demonstrates analysis at a more granular level than community areas.
    Tracts are smaller, so we can detect more localized patterns.
    """

    def __init__(self) -> None:
        """Initialize the tract analyzer."""
        super().__init__(
            "acs_tract_analysis",
            "Analyze correlations in census tract acs data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform tract-level analysis."""
        logger.info("Performing correlation analysis on tract acs data...")

        data = context["acs_tract_data"]

        # Prepare numeric columns for analysis
        numeric_cols = [
            "population_density",
            "median_house_income",
            "total_house_built_density",
            # "total_tenure_density",
            # "work_from_home",
            # "area_km2",
        ]

        # Remove rows with missing data
        analysis_data = data[numeric_cols].dropna()

        logger.info("Analyzing %d census tracts with complete data", len(analysis_data))

        # Calculate correlation matrix
        correlation_matrix = analysis_data.corr()

        # Key correlations to highlight
        key_correlations = {}

        for num_col1, num_col2 in combinations(correlation_matrix.columns, 2):
            key_correlations[f"{num_col1}{num_col2}"] = correlation_matrix.loc[
                num_col1, num_col1
            ]

        logger.info("Key Correlations Found:")
        for name, corr in key_correlations.items():
            strength = self._get_correlation_strength(abs(corr))
            logger.info("  %s: %.3f (%s)", name, corr, strength)

        return {
            "tract_correlation_matrix": correlation_matrix,
            "tract_analysis_data": analysis_data,
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
