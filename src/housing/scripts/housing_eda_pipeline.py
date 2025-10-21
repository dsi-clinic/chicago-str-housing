"""Chicago Housing EDA Pipeline.

This script demonstrates the full Chicago housing data analysis workflow:
1. Loading rental data and geographic boundaries (CSV with WKT geometries)
2. Spatial joins with many-to-many relationships (zip → tract → community)
3. Area-weighted aggregation across boundaries
4. Statistical analysis at multiple geographic levels
5. STR prohibition analysis and correlations
6. Airbnb data integration and density maps
"""

import logging

from housing.components.analyzers.rental_tract import RentalTractAnalyzer
from housing.components.analyzers.str_prohibition import STRProhibitionAnalyzer
from housing.components.loaders.acs_data import ACSLoader
from housing.components.loaders.airbnb_data import AirbnbDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.community_boundaries import CommunityBoundariesLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.acs_to_tract import ACSToTractProcessor
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.tract_to_community import TractToCommunityProcessor
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.airbnb_distribution import (
    AirbnbDistributionVisualizer,
)
from housing.components.visualizers.airbnb_map import AirbnbMapVisualizer
from housing.components.visualizers.rental_distribution import (
    RentalDistributionVisualizer,
)
from housing.components.visualizers.rental_map import RentalMapVisualizer
from housing.components.visualizers.str_distribution import STRDistributionVisualizer
from housing.components.visualizers.str_map import STRMapVisualizer
from housing.components.visualizers.str_prohibition_viz import STRProhibitionVisualizer
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
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(CityBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(AirbnbDataLoader())
    pipeline.register_component(ACSLoader())  # ACS Data

    # Step 2: Zip → Tract aggregation
    pipeline.register_component(ZipToTractProcessor())

    # Step 3: STR Prohibition → Tract aggregation (using existing processor)
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

    # Step 4: Airbnb → Tract aggregation (using existing processor)
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

    # Step 5: Tract → Community aggregation (the clean way!)
    pipeline.register_component(
        TractToCommunityProcessor(
            input_key="tract_rental_data",
            output_key="community_rental_data",
            id_column="tract_geoid",
            aggregate_columns={
                "avg_rental_price": ["mean", "min", "max"],
                "min_rental_price": "min",
                "max_rental_price": "max",
            },
            area_weighted_columns=["avg_rental_price"],
        )
    )

    # ACS Data with Geometry
    pipeline.register_component(
        ACSToTractProcessor(
            input_key="acs_data",
            output_key="acs_tract_data",
            calculate_density=True,
        )
    )

    # Step 6: Analyze at both levels
    pipeline.register_component(RentalTractAnalyzer())
    pipeline.register_component(STRProhibitionAnalyzer())

    # Step 7: Visualize rental distributions, STR analysis, and density maps
    pipeline.register_component(RentalDistributionVisualizer())
    pipeline.register_component(RentalMapVisualizer())
    pipeline.register_component(STRDistributionVisualizer())
    pipeline.register_component(STRMapVisualizer())
    pipeline.register_component(AirbnbDistributionVisualizer())
    pipeline.register_component(AirbnbMapVisualizer())
    pipeline.register_component(STRProhibitionVisualizer())

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Housing EDA Pipeline with STR Prohibition and Airbnb Analysis")
    logger.info("=" * 70)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 70)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
