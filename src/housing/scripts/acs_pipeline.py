"""Pipeline to test the ACS Data via API"""

import logging

from housing.components import (
    ACSCorrelationVisualizer,
    ACSIncomeVisualizer,
    ACSLoader,
    ACSMapVisualizer,
    ACSToTractProcessor,
    ACSTractAnalyzer,
    TractBoundariesLoader,
    TractToCommunityProcessor,
    RentalDataLoader,
    CommunityBoundariesLoader, 
    ZipBoundariesLoader,
    ZipToTractProcessor
)
from pipeline import Pipeline
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def create_acs_pipeline() -> Pipeline:
    """Create a pipeline that demonstrates core spatial data analysis concepts."""
    # 1. Create the pipeline with config
    config = PipelineConfig()
    pipeline = Pipeline("My ACS Data", config=config)
    pipeline.load_config()

    # 2. Register your components
    # Step 1: Load all boundaries
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(ACSLoader()) # ACS

    # Step 2:  Processor 
    pipeline.register_component(ZipToTractProcessor()) # Zip → Tract aggregation
    pipeline.register_component(ACSToTractProcessor())
    pipeline.register_component(TractToCommunityProcessor())

    # Step 3: Analyzer
    pipeline.register_component(ACSTractAnalyzer())

    # Step 4: visualizer
    pipeline.register_component(ACSCorrelationVisualizer())
    pipeline.register_component(ACSMapVisualizer())
    pipeline.register_component(ACSIncomeVisualizer())

    # 3. Run it!
    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Testing the ACS Pipeline")
    logger.info("=" * 45)
    pipeline, results = create_acs_pipeline()
