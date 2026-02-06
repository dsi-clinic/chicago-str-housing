"""DiD Pipeline"""

import logging

from housing.components.analyzers.did_analyzer import DIDAnalyzer
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.timeseries_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.time_series_zip_to_tract import (
    TimeSeriesZipToTractProcessor,
)
from housing.components.processors.tract_prohibition_dates import (
    TractProhibitionDatesProcessor,
)
from housing.components.processors.treatment_indicator import (
    TreatmentIndicatorProcessor,
)
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
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

    # Step 6: Load STR prohibition data
    logger.info("Step 6: Loading STR prohibition data...")
    pipeline.register_component(STRProhibitionDataLoader())

    # Step 7: Create tract prohibition dates
    logger.info("Step 7: Creating tract prohibition dates...")
    pipeline.register_component(TractProhibitionDatesProcessor())

    # Execute pipeline
    logger.info("Executing pipeline (steps 1-7)...")
    results = pipeline.execute()

    # Step 8: Create treatment indicators
    logger.info("Step 8: Creating treatment indicators...")
    treatment_processor = TreatmentIndicatorProcessor()
    treatment_result = treatment_processor.execute(pipeline.context)
    pipeline.context.update(treatment_result)
    results.append(
        PipelineResult(
            component_name="treatment_indicator",
            success=True,
            execution_time=0.0,
            data=treatment_result,
        )
    )

    # Step 9: Run descriptive analysis
    logger.info("Step 9: Running descriptive analysis...")
    descriptive_analyzer = DIDDescriptiveAnalyzer()
    analysis_result = descriptive_analyzer.execute(pipeline.context)
    pipeline.context.update(analysis_result)
    results.append(
        PipelineResult(
            component_name="did_descriptive_analysis",
            success=True,
            execution_time=0.0,
            data=analysis_result,
        )
    )

    # Step 10: Run DiD TWFE model analysis
    logger.info("Step 10: Running DiD TWFE model analysis...")
    did_analyzer = DIDAnalyzer()
    did_model_result = did_analyzer.execute(pipeline.context)
    pipeline.context.update(did_model_result)
    results.append(
        PipelineResult(
            component_name="did_twfe_analyzer",
            success=True,
            execution_time=0.0,
            data=did_model_result,
        )
    )

    # Step 11: Create visualizations
    logger.info("Step 11: Creating DiD trend visualizations...")
    output_dir = pipeline.context.get("output_dir", "output")
    trends_visualizer = DIDTrendsVisualizer(output_dir=output_dir)
    viz_result = trends_visualizer.execute(pipeline.context)
    pipeline.context.update(viz_result)
    results.append(
        PipelineResult(
            component_name="did_trends_visualization",
            success=True,
            execution_time=0.0,
            data=viz_result,
        )
    )

    return pipeline, results


if __name__ == "__main__":
    logger.info("DiD Pipeline")
    logger.info("=" * 70)

    pipeline, results = run_did_pipeline()

    logger.info("\n" + "=" * 70)
    logger.info("Pipeline complete!")
    logger.info("DiD panel available in pipeline.context['did_panel']")
    logger.info("Descriptive analysis results in pipeline.context")
    logger.info("=" * 70)
