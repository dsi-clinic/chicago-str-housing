"""Chicago Housing Difference-in-Differences (DiD) pipeline."""

import logging

from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.treatment_indicator import (
    TreatmentIndicatorProcessor,
)
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.time_series_str_map import (
    TimeSeriesSTRMapVisualizer,
)
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate housing DiD pipeline."""
    logger.info("Running Housing DiD Analysis")
    logger.info("=" * 70)

    pipeline = Pipeline("Housing DiD Analysis")

    # Step 1: Load all boundaries and data
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(TimeSeriesRentalLoader(output_dir="/project/output"))
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(
        CityBoundariesLoader()
    )  # Needed to filter tracts to Chicago

    # Step 2: Join rental data to boundaries
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column="application_id",
            aggregate_columns={
                "number_of_units": ["sum", "mean", "median"],
                "prohibition_date": ["min", "max"],
            },
            calculate_density=True,
            data_source_name="str_prohibition",
        )
    )
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(
        TimeSeriesZipToTractProcessor(output_dir="/project/output")
    )
    treatment_processor = TreatmentIndicatorProcessor(output_dir="/project/output")
    pipeline.register_component(treatment_processor)

    # Step 3: Descriptive analysis
    pipeline.register_component(DIDDescriptiveAnalyzer())

    # Step 4: Visualize the data
    pipeline.register_component(
        TimeSeriesSTRMapVisualizer(output_dir="/project/output")
    )
    pipeline.register_component(DIDTrendsVisualizer(output_dir="/project/output"))

    results = pipeline.execute()

    # Run validation if did_panel is in context
    if "did_panel" in pipeline.context:
        logger.info("Running validation on treatment indicator...")
        treatment_processor.run_validation(pipeline.context)

    return pipeline, results


if __name__ == "__main__":
    logger.info("Housing DiD Pipeline with STR Prohibition and ZORI dataset.")
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
