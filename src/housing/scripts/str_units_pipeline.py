"""Chicago Housing EDA Pipeline – STR Units"""

import logging

from housing.components.analyzers.str_units_analyzer import STRUnitsTractAnalyzer
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.community_boundaries import CommunityBoundariesLoader
from housing.components.loaders.str_data import STRDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.processors.outlier_removal import DensityOutlierRemovalProcessor
from housing.components.processors.str_units_point_to_tract import (
    STRUnitsToTractProcessor,
)
from housing.components.processors.str_units_tract_to_community import (
    STRUnitsToCommunityProcessor,
)
from housing.components.visualizers.str_units_count_distribution import (
    STRUnitsCountDistributionVisualizer,
)
from housing.components.visualizers.str_units_density_distribution import (
    STRUnitsDensityDistributionVisualizer,
)
from housing.components.visualizers.str_units_density_maps import STRUnitsDensityMaps
from housing.components.visualizers.str_units_maps import STRUnitsMapVisualizer
from housing.components.visualizers.str_units_top10 import STRUnitsTop10
from pipeline import Pipeline, PipelineResult
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def run_str_units_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run Housing EDA analysis for STR Units only."""
    logger.info("Running STR Units EDA Analysis")
    logger.info("=" * 70)

    config = PipelineConfig()
    pipeline = Pipeline("Housing EDA – STR Units", config=config)
    pipeline.load_config()

    # Load base data
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(STRDataLoader())

    # Process STR Units data
    pipeline.register_component(STRUnitsToTractProcessor())
    pipeline.register_component(
        DensityOutlierRemovalProcessor(
            input_key="str_units_tract_data",
            output_key="str_units_tract_data",
            density_columns="str_units_density",
            method="winsorize",
            percentile_threshold=0.99,
        )
    )
    pipeline.register_component(STRUnitsToCommunityProcessor())

    # Analyze + visualize
    pipeline.register_component(STRUnitsTractAnalyzer())
    pipeline.register_component(STRUnitsMapVisualizer())
    pipeline.register_component(STRUnitsCountDistributionVisualizer())
    pipeline.register_component(STRUnitsDensityDistributionVisualizer())
    pipeline.register_component(STRUnitsTop10())
    pipeline.register_component(STRUnitsDensityMaps())

    results = pipeline.execute()
    return pipeline, results


if __name__ == "__main__":
    logger.info("Pipeline – STR Units")
    logger.info("=" * 70)
    pipeline, results = run_str_units_analysis()
    logger.info("Pipeline run complete – check output directory for visualizations.")
