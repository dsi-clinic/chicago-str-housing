"""Difference-in-Differences Time-Series Analysis Pipeline.

This script demonstrates the DiD analysis workflow:
1. Loading time-series rental data from csv file
2. Spatial join to convert zip code data to Census tract level
3. Build DiD panel dataset with treatment variables
4. Analyze and visualize DiD data before experiment
"""

import logging

from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.tract_prohibition_dates import (
    TractProhibitionDatesProcessor,
)
from housing.components.processors.treatment_threshold import (
    TreatmentThresholdProcessor,
)
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.treatment_map import TreatmentMapVisualizer
from housing.did_spec import DID_TREATMENT_THRESHOLD_PERCENTILE
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
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(TimeSeriesRentalLoader())
    pipeline.register_component(
        CensusDataLoader(api_key="2a9cd1fa2e1158252a3f3810be0589b6d9ef41a0")
    )

    # Load point-in-time data and use it to build the crosswalk
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipToTractProcessor())

    # Use crosswalk to convert panel data to tract-level
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    # Build treatment variable
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column="application_id",
            aggregate_columns={
                "prohibition_date": "min",
                "number_of_units": "sum",
            },
            calculate_density=True,
            data_source_name="str_prohibition",
        )
    )
    pipeline.register_component(TractProhibitionDatesProcessor())
    # pipeline.register_component(TreatmentIndicatorProcessor())
    pipeline.register_component(
        TreatmentThresholdProcessor(
            percentile=DID_TREATMENT_THRESHOLD_PERCENTILE,
        )
    )

    # Conduct pre-experiment analysis
    pipeline.register_component(DIDDescriptiveAnalyzer())
    pipeline.register_component(DIDTrendsVisualizer())
    pipeline.register_component(TreatmentMapVisualizer())

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
