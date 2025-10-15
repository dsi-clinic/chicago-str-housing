"""Pipeline to test the ACS Data via API"""

import logging

from housing.components import ACSLoader, ACSToTractProcessor, TractBoundariesLoader
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
    pipeline.register_component(ACSLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ACSToTractProcessor())

    # 3. Run it!
    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Testing the ACS Pipeline")
    logger.info("=" * 45)
    pipeline, results = create_acs_pipeline()
