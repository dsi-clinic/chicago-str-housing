"""Utility functions for housing analysis.

This module contains helper functions and utilities used across housing components.
"""

import logging
from typing import Any

from housing.components.constants import (
    MODERATE_CORRELATION_THRESHOLD,
    STRONG_CORRELATION_THRESHOLD,
)
from pipeline.base import pipeline_component

logger = logging.getLogger(__name__)


@pipeline_component(
    name="summary_reporter", description="Generate a summary report of the analysis"
)
def summary_reporter(context: dict[str, Any]) -> dict[str, Any]:
    """Generate a summary report of the analysis.

    This demonstrates how to create summary reports from pipeline results.
    """
    logger.info("Generating summary report...")
    print("\n" + "=" * 60)
    print("SPATIAL DATA ANALYSIS SUMMARY REPORT")
    print("=" * 60)

    # Get summary stats
    summary_stats = context.get("summary_stats", {})

    print("\nDataset Overview:")
    print(f"  • Total Community Areas: {summary_stats.get('total_communities', 'N/A')}")
    print(
        f"  • Areas with Rental Data: {summary_stats.get('communities_with_data', 'N/A')}"
    )

    print("\nRental Price Statistics:")
    print(f"  • Average: ${summary_stats.get('avg_rental_price', 0):,.0f}")
    print(f"  • Standard Deviation: ${summary_stats.get('rental_price_std', 0):,.0f}")

    print("\nKey Insights:")
    correlations = summary_stats.get("key_correlations", {})
    for name, corr in correlations.items():
        strength = (
            "Strong"
            if abs(corr) >= STRONG_CORRELATION_THRESHOLD
            else "Moderate"
            if abs(corr) >= MODERATE_CORRELATION_THRESHOLD
            else "Weak"
        )
        print(f"  • {name}: {corr:.3f} ({strength})")

    return {"report_generated": True}
