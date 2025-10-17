"""Foreclosed rental property EDA pipeline."""

import logging

from housing import CommunityBoundariesLoader, ForeclosedDataLoader, PointsToTractProcessor, TractToCommunityProcessor
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
    pipeline.register_component(CommunityBoundariesLoader())

    # Step 2: Points → Tract aggregation
    pipeline.register_component(PointsToTractProcessor())

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
