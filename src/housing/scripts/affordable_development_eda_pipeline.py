import logging

from housing.components.loaders.affordable_development_data import AffordableDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.community_boundaries import CommunityBoundariesLoader
from housing.components.processors.affordable_development_points_to_tract import AffordableTractDensityProcessor
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.visualizers.affordable_development_distribution import AffordableDistributionVisualizer
from housing.components.visualizers.affordable_development_map import AffordableMapVisualizer
from housing.components.loaders.airbnb_data import AirbnbDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.analyzers.affordable_development_tract_correlation import AffordableCorrelationAnalyzer


from pipeline import Pipeline, PipelineResult
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)

affordable_points_to_tract = PointsToTractProcessor(
    input_key="affordable_developments_data",
    output_key="affordable_developments_tract_data", 
    id_column="property_name",
    aggregate_columns={"units": ["sum"]}
)

affordable_points_to_tract = PointsToTractProcessor(
    input_key="affordable_developments_data",
    output_key="affordable_developments_tract_data", 
    id_column="property_name",
    aggregate_columns={"units": ["sum"]}
)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Affordable Housing EDA analysis."""
    logger.info("Running Affordable Development EDA Analysis")
    logger.info("=" * 50)

    config = PipelineConfig()
    pipeline = Pipeline("Affordable Development EDA", config=config)
    pipeline.load_config()

    # Step 1: Load all boundaries
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(AffordableDataLoader())

    # Step 2: Tract-level data aggregation
    pipeline.register_component(affordable_points_to_tract)
    pipeline.register_component(AffordableTractDensityProcessor())

    # Step 3: Community aggregation (ability to add later if useful)
    #pipeline.register_component(AffordableCommunityDensityProcessor())

    # Step 4: Load in and get correlation analysis with other data
    pipeline.register_component(AirbnbDataLoader())
    pipeline.register_component(STRProhibitionDataLoader())

    pipeline.register_component(
        PointsToTractProcessor(
            input_key="str_prohibition_data",
            output_key="str_tract_data",
            id_column="application_id",
            aggregate_columns={
                "number_of_units": ["sum", "mean", "median"],
            },
            calculate_density=True,
        )
    )

    pipeline.register_component(
        PointsToTractProcessor(
            input_key="airbnb_data",
            output_key="airbnb_tract_data",
            id_column="id",
            aggregate_columns={
                "price_numeric": ["mean", "median", "min", "max"],
            },
            calculate_density=True,
        )
    )

    pipeline.register_component(AffordableCorrelationAnalyzer())


    # Step 5: Visualize rental distributions at both levels
    pipeline.register_component(AffordableDistributionVisualizer())
    pipeline.register_component(AffordableMapVisualizer())

    results = pipeline.execute()


    return pipeline, results


if __name__ == "__main__":
    logger.info("Affordable Development EDA Pipeline - Minimal Demo")
    logger.info("=" * 50)

    pipeline, results = run_full_analysis()
