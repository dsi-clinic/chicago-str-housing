"""Chicago Housing EDA Pipeline (STR Data Only)"""

import logging

from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.community_boundaries import CommunityBoundariesLoader
from housing.components.loaders.str_data import STRDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.processors.outlier_removal import DensityOutlierRemovalProcessor
from housing.components.processors.str_buildings_point_to_tract import (
    STRBuildingsToTractProcessor,
)
from housing.components.processors.str_buildings_tract_to_community import (
    STRBuildingsToCommunityProcessor,
)
from pipeline import Pipeline, PipelineResult
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate housing EDA analysis with STR prohibition and Airbnb integration."""
    logger.info("Running Housing EDA Analysis with STR Prohibitions and Airbnb")
    logger.info("=" * 70)

    config = PipelineConfig()
    pipeline = Pipeline("Housing EDA with STR and Airbnb Analysis", config=config)
    pipeline.load_config()

    # Step 1: Load all boundaries and data
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(STRDataLoader())

    pipeline.register_component(STRBuildingsToTractProcessor())
    pipeline.register_component(
        DensityOutlierRemovalProcessor(
            input_key="str_buildings_tract_data",
            output_key="str_buildings_tract_data_clean",
            density_columns="str_buildings_density",
            method="iqr",
        )
    )
    pipeline.register_component(STRBuildingsToCommunityProcessor())

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Housing EDA Pipeline with STR Data")
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete")
    # logger.info("Demo complete! Check the output/ directory for visualizations.")
