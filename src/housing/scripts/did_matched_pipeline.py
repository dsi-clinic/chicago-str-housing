"""DiD Matched Pipeline - Runs DiD analysis on trend-matched sample."""

import logging

from housing.components.analyzers.did_analyzer import DIDAnalyzer
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
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
from housing.components.processors.trend_matching import TrendMatchingProcessor
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.event_study import EventStudyVisualizer
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_did_matched_pipeline() -> tuple[Pipeline, list[PipelineResult]]:
    """Run DiD analysis on trend-matched sample."""
    logger.info("Running DiD Matched Pipeline")
    logger.info("=" * 70)

    pipeline = Pipeline("DiD Matched Pipeline")
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

    # Execute pipeline to get did_panel
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

    # Step 9: Trend matching
    logger.info("Step 9: Matching treated tracts to controls by pre-treatment trends...")
    trend_matcher = TrendMatchingProcessor(k_neighbors=3, min_pre_periods=6)
    matching_result = trend_matcher.execute(pipeline.context)
    pipeline.context.update(matching_result)
    results.append(
        PipelineResult(
            component_name="trend_matching",
            success=True,
            execution_time=0.0,
            data=matching_result,
        )
    )

    # Step 10: Run descriptive analysis on matched sample
    logger.info("Step 10: Running descriptive analysis on matched sample...")
    descriptive_analyzer = DIDDescriptiveAnalyzer()
    analysis_result = descriptive_analyzer.execute(pipeline.context)
    pipeline.context.update(analysis_result)
    results.append(
        PipelineResult(
            component_name="did_descriptive_analysis_matched",
            success=True,
            execution_time=0.0,
            data=analysis_result,
        )
    )

    # Step 11: Run DiD TWFE model on matched sample
    logger.info("Step 11: Running DiD TWFE model on matched sample...")
    did_analyzer = DIDAnalyzer()
    did_model_result = did_analyzer.execute(pipeline.context)
    pipeline.context.update(did_model_result)
    
    # Save matched TWFE results to file
    import json
    from pathlib import Path
    base_output_dir = pipeline.context.get("output_dir", "output")
    matched_output_path = Path(base_output_dir) / "did_twfe_results_matched.json"
    matched_output_path.parent.mkdir(parents=True, exist_ok=True)
    matched_output_path.write_text(
        json.dumps(did_model_result["did_twfe_results"]["stats"], indent=2)
    )
    logger.info("Saved matched TWFE results to %s", matched_output_path)
    
    results.append(
        PipelineResult(
            component_name="did_twfe_analyzer_matched",
            success=True,
            execution_time=0.0,
            data=did_model_result,
        )
    )

    # Step 12: Run event study analysis on matched sample
    logger.info("Step 12: Running event study analysis on matched sample...")
    event_study_analyzer = EventStudyAnalyzer(event_window=12)
    event_study_result = event_study_analyzer.execute(pipeline.context)
    pipeline.context.update(event_study_result)
    
    # Save matched event study coef_df to file
    coef_df = event_study_result["event_study_coef_df"]
    matched_coef_path = Path(base_output_dir) / "event_study_coef_df_matched.csv"
    coef_df.to_csv(matched_coef_path, index=False)
    logger.info("Saved matched event study coefficients to %s", matched_coef_path)
    
    results.append(
        PipelineResult(
            component_name="event_study_analysis_matched",
            success=True,
            execution_time=0.0,
            data=event_study_result,
        )
    )

    # Step 13: Create DiD trend visualizations on matched sample
    logger.info("Step 13: Creating DiD trend visualizations on matched sample...")
    base_output_dir = pipeline.context.get("output_dir", "output")
    trends_visualizer = DIDTrendsVisualizer(
        output_dir=base_output_dir, file_suffix="_matched"
    )
    viz_result = trends_visualizer.execute(pipeline.context)
    pipeline.context.update(viz_result)
    results.append(
        PipelineResult(
            component_name="did_trends_visualization_matched",
            success=True,
            execution_time=0.0,
            data=viz_result,
        )
    )

    # Step 14: Create event study visualization on matched sample
    logger.info("Step 14: Creating event study visualization on matched sample...")
    event_study_viz = EventStudyVisualizer(
        output_dir=base_output_dir, file_suffix="_matched"
    )
    event_viz_result = event_study_viz.execute(pipeline.context)
    pipeline.context.update(event_viz_result)
    results.append(
        PipelineResult(
            component_name="event_study_visualization_matched",
            success=True,
            execution_time=0.0,
            data=event_viz_result,
        )
    )

    return pipeline, results


if __name__ == "__main__":
    logger.info("DiD Matched Pipeline")
    logger.info("=" * 70)

    pipeline, results = run_did_matched_pipeline()

    logger.info("\n" + "=" * 70)
    logger.info("Matched pipeline complete!")
    logger.info("Matched DiD panel available in pipeline.context['did_panel']")
    logger.info("All results available in pipeline.context")
    logger.info("=" * 70)
