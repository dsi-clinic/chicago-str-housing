"""Chicago Housing DiD Pipeline.

This script demonstrates the full DiD workflow:
1. Loading rental data and geographic boundaries (time series data)
"""

import logging

from housing.components.loaders.time_series_rental_data import (
    TimeSeriesRentalDataLoader,
)
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate housing DiD analysis."""
    logger.info("Running Housing DiD Analysis")
    logger.info("=" * 70)

    pipeline = Pipeline("Housing DiD Analysis")

    # Step 1: Load all data
    pipeline.register_component(TimeSeriesRentalDataLoader())

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Housing DiD Pipeline")
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check the output/ directory for visualizations.")