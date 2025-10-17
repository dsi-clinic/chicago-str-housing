"""Foreclosed rental property EDA pipeline."""

import logging

from housing import CommunityBoundariesLoader, ForeclosedDataLoader, PointsToTractProcessor, TractBoundariesLoader, TractToCommunityProcessor, ZipBoundariesLoader, ZipToTractProcessor, RentalDataLoader
from pipeline import Pipeline, PipelineResult
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)

def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate foreclosed rental property EDA analysis."""
    logger.info("Running Foreclosed Rental Property EDA Analysis")
    logger.info("=" * 50)

    config = PipelineConfig()

    pipeline = Pipeline("Foreclosed EDA", config=config)
    pipeline.load_config()
    
    # Step 1: Load necessary data
    pipeline.register_component(ForeclosedDataLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(RentalDataLoader())

    # Step 2: Points → Tract aggregation
    processor = PointsToTractProcessor(
        input_key="foreclosed_data",
        output_key="foreclosed_tract_data",
        id_column="ID",
        aggregate_columns={
        },
        calculate_density=True
    )

    pipeline.register_component(processor)

    pipeline.register_component(ZipToTractProcessor())

    # Step 3: Tract → Community aggregation
    pipeline.register_component(TractToCommunityProcessor())

    results = pipeline.execute()

    return pipeline, results

if __name__ == "__main__":
    logger.info("Foreclosed EDA Pipeline - Minimal Demo")
    logger.info("=" * 50)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 50)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
