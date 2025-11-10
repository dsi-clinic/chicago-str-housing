"""Testing STR pipeline with choropleth mapping"""

import logging

from housing.components.analyzers.str_prohibition import STRProhibitionAnalyzer
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.community_boundaries import CommunityBoundariesLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.outlier_removal import DensityOutlierRemovalProcessor
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.tract_to_community import TractToCommunityProcessor
from housing.components.visualizers.str_choropleth_mapping import (
    STRChoroplethSchemesVisualizer,
)
from housing.components.visualizers.str_distribution import STRDistributionVisualizer
from housing.components.visualizers.str_map import STRMapVisualizer
from housing.components.visualizers.str_prohibition_viz import STRProhibitionVisualizer
from pipeline import Pipeline
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, dict]:
    """Run the full housing STR EDA pipeline with choropleth visualization."""
    logger.info("Running Housing EDA Analysis with STR Prohibitions and Airbnb")
    logger.info("=" * 70)

    config = PipelineConfig()
    pipeline = Pipeline("Housing EDA with STR and Airbnb Analysis", config=config)
    pipeline.load_config()

    # Loading all data
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))

    # Aggregation, from point to tract
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column="application_id",
            aggregate_columns={"number_of_units": ["sum", "mean", "median"]},
            calculate_density=True,
            data_source_name="str_prohibition",
        )
    )

    # Winsorize density outliers
    pipeline.register_component(
        DensityOutlierRemovalProcessor(
            input_key="str_tract_data",
            output_key="str_tract_data",
            density_columns=["str_prohibition_density"],
            method="winsorize",
            percentile_threshold=0.99,
        )
    )

    # Aggregation, from tract to community level
    pipeline.register_component(
        TractToCommunityProcessor(
            input_key="str_tract_data",
            output_key="str_community_data",
            id_column="tract_geoid",
            area_weighted_columns=["str_prohibition_density"],
            aggregate_columns={"str_prohibition_count": "sum"},
        )
    )

    # Analyzers
    pipeline.register_component(STRProhibitionAnalyzer())

    # Visualizers
    pipeline.register_component(STRDistributionVisualizer())
    pipeline.register_component(STRMapVisualizer())
    pipeline.register_component(STRProhibitionVisualizer())
    pipeline.register_component(STRChoroplethSchemesVisualizer())

    # Execute pipline
    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("STR Clustering Pipeline with STR Prohibition and Airbnb Analysis")
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
