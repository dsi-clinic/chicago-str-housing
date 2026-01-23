"""Tract Panel Pipeline.

This script creates a tract-level rental price panel from ZIP-level time series data:
1. Load ZIP and tract boundaries
2. Load rental data (for crosswalk creation)
3. Create ZIP-to-tract crosswalk using spatial joins
4. Load time series rental panel data (ZIP-level)
5. Convert ZIP-level panel to tract-level panel using crosswalk
"""

import logging

from src.housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.timeseries_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_tract_panel_pipeline() -> tuple[Pipeline, list[PipelineResult]]:
    """Create tract-level rental price panel from ZIP-level time series data.

    Returns:
        Tuple of (pipeline, results)
    """
    logger.info("Running Tract Panel Pipeline")
    logger.info("=" * 70)

    pipeline = Pipeline("Tract Panel Pipeline")
    pipeline.load_config()

    # Step 1: Load boundaries
    logger.info("Step 1: Loading geographic boundaries...")
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())

    # Step 2: Load rental data (needed for crosswalk creation)
    logger.info("Step 2: Loading rental data for crosswalk...")
    pipeline.register_component(RentalDataLoader())

    # Step 3: Create ZIP-to-tract crosswalk (spatial join)
    # This creates the mapping between ZIP codes and tracts with area weights
    logger.info("Step 3: Creating ZIP-to-tract crosswalk...")
    pipeline.register_component(ZipToTractProcessor())

    # Step 4: Load time series rental panel data (ZIP-level)
    logger.info("Step 4: Loading time series rental panel data...")
    pipeline.register_component(TimeSeriesRentalLoader())

    # Step 5: Convert ZIP-level panel to tract-level panel using crosswalk
    logger.info("Step 5: Converting to tract-level panel...")
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    # Execute pipeline
    logger.info("Executing pipeline...")
    results = pipeline.execute()

    # Log summary
    logger.info("\n" + "=" * 70)
    logger.info("Pipeline execution summary:")
    for result in results:
        status = "✓" if result.success else "✗"
        logger.info(
            "  %s %s (%.2f seconds)",
            status,
            result.component_name,
            result.execution_time,
        )
        if not result.success and result.error:
            logger.error("    Error: %s", result.error)

    # Check final output
    if "tract_panel_data" in pipeline.context:
        tract_panel = pipeline.context["tract_panel_data"]
        logger.info("\n" + "=" * 70)
        logger.info("Tract Panel Summary:")
        logger.info("  Total rows: %d", len(tract_panel))
        logger.info("  Unique tracts: %d", tract_panel["tract_geoid"].nunique())
        logger.info("  Unique months: %d", tract_panel["month"].nunique())
        logger.info(
            "  Date range: %s to %s",
            tract_panel["month"].min(),
            tract_panel["month"].max(),
        )
        logger.info(
            "  Rental price range: $%.2f - $%.2f",
            tract_panel["rental_price"].min(),
            tract_panel["rental_price"].max(),
        )

    return pipeline, results


if __name__ == "__main__":
    logger.info("Tract Panel Pipeline")
    logger.info("=" * 70)

    pipeline, results = run_tract_panel_pipeline()

    logger.info("\n" + "=" * 70)
    logger.info("Pipeline complete!")
    logger.info("Tract panel data available in pipeline.context['tract_panel_data']")
    logger.info("=" * 70)
