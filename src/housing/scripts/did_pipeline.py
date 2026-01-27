"""Chicago Housing Difference-in-Differences (DiD) pipeline."""

import logging

from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate housing DiD pipeline."""
    logger.info("Running Housing DiD Analysis")
    logger.info("=" * 70)

    pipeline = Pipeline("Housing DiD Analysis")

    # Step 1: Load all boundaries and data
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(TimeSeriesRentalLoader(output_dir="/project/output"))
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())

    # Step 2: Join rental data to boundaries
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor(output_dir="/project/output"))

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Housing DiD Pipeline with STR Prohibition and ZORI dataset.")
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
