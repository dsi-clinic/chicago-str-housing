"""Chicago Housing EDA Pipeline – STR Buildings"""

import logging

from housing.components.analyzers.str_buildings_analyzer import (
    STRBuildingsTractAnalyzer,
)
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
from housing.components.visualizers.str_buildings_count_distribution import (
    STRBuildingsCountDistributionVisualizer,
)
from housing.components.visualizers.str_buildings_density_distribution import (
    STRBuildingsDensityDistributionVisualizer,
)
from housing.components.visualizers.str_buildings_maps import STRBuildingsMapVisualizer
from housing.components.visualizers.str_buildings_top_10 import STRBuildingsTop10
from pipeline import Pipeline, PipelineResult
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def run_str_buildings_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run Housing EDA analysis for STR Buildings only."""
    logger.info("Running STR Buildings EDA Analysis")
    logger.info("=" * 70)

    config = PipelineConfig()
    pipeline = Pipeline("Housing EDA - STR Buildings", config=config)
    pipeline.load_config()

    # Load base data
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(STRDataLoader())

    # Process STR Buildings data
    pipeline.register_component(STRBuildingsToTractProcessor())
    pipeline.register_component(
        DensityOutlierRemovalProcessor(
            input_key="str_buildings_tract_data",
            output_key="str_buildings_tract_data",
            density_columns="str_buildings_density",
            method="winsorize",
            percentile_threshold=0.99,
        )
    )
    pipeline.register_component(STRBuildingsToCommunityProcessor())

    # Analyze + visualize
    pipeline.register_component(STRBuildingsTractAnalyzer())
    pipeline.register_component(STRBuildingsMapVisualizer())
    pipeline.register_component(STRBuildingsCountDistributionVisualizer())
    pipeline.register_component(STRBuildingsDensityDistributionVisualizer())
    pipeline.register_component(STRBuildingsTop10())

    results = pipeline.execute()
    return pipeline, results


if __name__ == "__main__":
    logger.info("Pipeline – STR Buildings")
    logger.info("=" * 70)
    pipeline, results = run_str_buildings_analysis()
    logger.info("Pipeline run complete – check output directory for visualizations.")
