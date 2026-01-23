"""Difference-in-Differences Time-Series Analysis Pipeline.

This script demonstrates the DiD analysis workflow:
1. Loading time-series rental data from csv file
2. Spatial join to convert zip code data to Census tract level
3. work in progress, future steps coming ...
"""

import logging

from housing.components.loaders.time_series_rental import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate DiD Time-Series Analysis of Rental Prices"""
    logger.info("Running DiD Time-Series Analysis of Rental Prices")
    logger.info("=" * 70)

    pipeline = Pipeline("DiD Time-Series Analysis of Rental Prices")

    # Load boundaries and data
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(TimeSeriesRentalLoader())

    #Load point-in-time data and use it to build the crosswalk
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipToTractProcessor())

    #Use crosswalk to convert panel data to tract-level
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info(
        "DiD Time-Series Analysis Pipeline for STR Prohibitions and Rental Prices"
    )
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
