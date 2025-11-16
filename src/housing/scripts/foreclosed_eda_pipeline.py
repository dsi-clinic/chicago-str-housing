"""Foreclosed Data EDA Pipeline.

This script demonstrates the foreclosed data analysis workflow:
1. Loading foreclosed rental data from API
2. Spatial joins and boundary aggregations
"""

import logging

from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.community_boundaries import CommunityBoundariesLoader
from housing.components.loaders.foreclosed_data import ForeclosedDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.processors.points_to_tract import (
    PointsToTractProcessor,
)
from housing.components.processors.tract_to_community import (
    TractToCommunityProcessor,
)
from housing.components.visualizers.foreclosed_distribution import (
    ForeclosedDistributionVisualizer,
)
from housing.components.visualizers.foreclosed_map import ForeclosedMapVisualizer
from pipeline import Pipeline, PipelineResult

logger = logging.getLogger(__name__)


def run_foreclosed_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate foreclosed EDA analysis."""
    logger.info("Running Foreclosed EDA Analysis")
    logger.info("=" * 70)

    pipeline = Pipeline("Foreclosed EDA Analysis")

    # Step 1: Load all boundaries and foreclosed data
    pipeline.register_component(ForeclosedDataLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())

    # Step 2: Join foreclosed points to boundaries
    pipeline.register_component(
        PointsToTractProcessor(
            input_key="foreclosed_data",
            output_key="foreclosed_tract_data",
            id_column="id",
            aggregate_columns={},
            data_source_name="foreclosed",
        )
    )

    pipeline.register_component(
        TractToCommunityProcessor(
            input_key="foreclosed_tract_data",
            output_key="foreclosed_community_data",
            id_column="tract_geoid",
            aggregate_columns={"foreclosed_count": "sum", "foreclosed_density": "mean"},
        )
    )

    # Step 3: Visualize foreclosed data on map
    pipeline.register_component(ForeclosedMapVisualizer())
    pipeline.register_component(ForeclosedDistributionVisualizer())

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Foreclosed EDA Pipeline")
    logger.info("=" * 70)

    pipline, results = run_foreclosed_analysis()

    logger.info("\n" + "=" * 70)
    logger.info(
        "Foreclosed EDA Pipeline Complete. Check the output/ directory for visualizations"
    )
