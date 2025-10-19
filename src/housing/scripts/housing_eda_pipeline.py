"""Chicago Housing EDA Pipeline.

This script demonstrates the full Chicago housing data analysis workflow:
1. Loading rental data and geographic boundaries (CSV with WKT geometries)
2. Spatial joins with many-to-many relationships (zip → tract → community)
3. Area-weighted aggregation across boundaries
4. Statistical analysis at multiple geographic levels

This is the complete housing analysis pipeline that students will use.
"""

import logging

from housing import (
    CommunityBoundariesLoader,
    RentalCorrelationAnalyzer,
    RentalDataLoader,
    RentalDistributionVisualizer,
    RentalMapVisualizer,
    RentalTractAnalyzer,
    TractBoundariesLoader,
    TractToCommunityProcessor,
    ZipBoundariesLoader,
    ZipToTractProcessor,
)
from pipeline import Pipeline, PipelineResult
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate housing EDA analysis."""
    logger.info("Running Housing EDA Analysis")
    logger.info("=" * 50)

    config = PipelineConfig()
    pipeline = Pipeline("Housing EDA", config=config)
    pipeline.load_config()

    # Step 1: Load all boundaries
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())

    # Step 2: Zip → Tract aggregation
    pipeline.register_component(ZipToTractProcessor())

    # Step 3: Tract → Community aggregation (the clean way!)
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

    # Step 4: Analyze at both levels
    pipeline.register_component(RentalTractAnalyzer())
    pipeline.register_component(RentalCorrelationAnalyzer())

    # Step 5: Visualize rental distributions at both levels
    pipeline.register_component(RentalDistributionVisualizer())
    pipeline.register_component(RentalMapVisualizer())

    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    logger.info("Housing EDA Pipeline - Minimal Demo")
    logger.info("=" * 50)

    pipeline, results = run_full_analysis()

    logger.info("\n" + "=" * 50)
    logger.info("Demo complete! Check the output/ directory for visualizations.")
