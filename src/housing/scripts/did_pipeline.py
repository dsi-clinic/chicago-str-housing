"""Chicago Housing DiD Pipeline.

This script demonstrates the full DiD workflow:
1. Loading rental data and geographic boundaries (time series data)
"""

import logging

from housing.components.analyzers.did_analyzer import DIDAnalyzer
from housing.components.analyzers.did_descriptive_analyzer import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study_analysis import EventStudyAnalyzer
from housing.components.loaders.census_data import CensusDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental_data import (
    TimeSeriesRentalLoader,
)
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.tract_panel import (
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
from housing.components.visualizers.event_study_plot import EventStudyVisualizer
from housing.components.visualizers.treatment_map import TreatmentMapVisualizer
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate housing DiD analysis."""
    logger.info("Running Housing DiD Analysis")
    logger.info("=" * 70)

    pipeline = Pipeline("Housing DiD Analysis")

    # Step 1: Load all data
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(TimeSeriesRentalLoader())
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(
        CensusDataLoader(api_key="2a9cd1fa2e1158252a3f3810be0589b6d9ef41a0")
    )
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))

    # Step 2: Aggregate time series rental data to tracts
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())

    # Step 3: STR Prohibition → Tract aggregation (using improved processor)
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

    # Step 3.5: STR Prohibition Dates → Tract aggregation
    pipeline.register_component(TractProhibitionDatesProcessor())
    # pipeline.register_component(TreatmentIndicatorProcessor())
    pipeline.register_component(TreatmentThresholdProcessor())

    # Step 4: DID Analysis
    pipeline.register_component(DIDDescriptiveAnalyzer())
    pipeline.register_component(DIDAnalyzer())
    pipeline.register_component(EventStudyAnalyzer())

    # Step 5: Visualizations
    pipeline.register_component(DIDTrendsVisualizer())
    pipeline.register_component(TreatmentMapVisualizer())
    pipeline.register_component(EventStudyVisualizer())

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Housing DiD Pipeline")
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
