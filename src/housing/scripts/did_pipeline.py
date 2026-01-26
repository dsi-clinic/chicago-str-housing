"""DiD Pipeline"""

import logging

from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.timeseries_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_did_pipeline() -> tuple[Pipeline, list[PipelineResult]]:
    """Run DiD analysis."""
    logger.info("Running DiD Pipeline")
    logger.info("=" * 70)

    pipeline = Pipeline("DiD Pipeline")
    pipeline.load_config()

    # Step 1: Load boundaries
    logger.info("Step 1: Loading geographic boundaries...")
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())

    # Step 2: Load rental data
    logger.info("Step 2: Loading rental data for crosswalk...")
    pipeline.register_component(RentalDataLoader())

    # Step 3: Create ZIP-to-tract crosswalk
    logger.info("Step 3: Creating ZIP-to-tract crosswalk...")
    pipeline.register_component(ZipToTractProcessor())

    # Step 4: Load time series rental panel data
    logger.info("Step 4: Loading time series rental panel data...")
    pipeline.register_component(TimeSeriesRentalLoader())

    # Step 5: Convert ZIP-level panel to tract-level panel using crosswalk
    logger.info("Step 5: Converting to tract-level panel...")
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    # Execute pipeline
    logger.info("Executing pipeline...")
    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("DiD Pipeline")
    logger.info("=" * 70)

    pipeline, results = run_did_pipeline()

    logger.info("\n" + "=" * 70)
    logger.info("Pipeline complete!")
    logger.info("=" * 70)
