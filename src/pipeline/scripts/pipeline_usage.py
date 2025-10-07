"""Example usage of the Spatial Data Analysis Pipeline.

This script demonstrates the core spatial data analysis concepts:
1. Loading data from different formats (CSV, GeoJSON)
2. Spatial joins and geometry transformations
3. Aggregating data across spatial boundaries
4. Statistical analysis on merged datasets

This is designed for educational use to teach students the most challenging
aspects of spatial data analysis.
"""

import logging
from typing import Any

from pipeline import (
    CommunityBoundariesLoader,
    CorrelationAnalyzer,
    CorrelationVisualizer,
    Pipeline,
    PipelineResult,
    RentalDataLoader,
    SpatialJoinProcessor,
    ZipBoundariesLoader,
    pipeline_component,
    summary_reporter,
)
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def create_spatial_analysis_pipeline() -> Pipeline:
    """Create a pipeline that demonstrates core spatial data analysis concepts."""
    # Load configuration
    config = PipelineConfig()
    pipeline = Pipeline("Spatial Data Analysis Demo", config=config)
    pipeline.load_config()

    # Step 1: Load data from different sources (using config paths)
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())

    # Step 2: Perform spatial join (the hard part!)
    pipeline.register_component(SpatialJoinProcessor())

    # Step 3: Analyze the merged dataset
    pipeline.register_component(CorrelationAnalyzer())
    pipeline.register_component(CorrelationVisualizer())
    pipeline.register_component(summary_reporter)

    return pipeline


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the complete spatial analysis pipeline."""
    logger.info("Starting Spatial Data Analysis Pipeline")
    logger.info("=" * 50)

    pipeline = create_spatial_analysis_pipeline()
    results = pipeline.execute()

    logger.info("Pipeline execution completed!")
    logger.info("Generated %d results:", len(results))
    for result in results:
        status = "SUCCESS" if result.success else "FAILED"
        logger.info("  • %s: %s", result.component_name, status)

    return pipeline, results


def run_partial_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run only the data loading and spatial join parts."""
    logger.info("Running Partial Analysis (Data Loading + Spatial Join)")
    logger.info("=" * 55)

    # Load configuration
    config = PipelineConfig()
    pipeline = Pipeline("Partial Spatial Analysis", config=config)
    pipeline.load_config()

    # Only load data and perform spatial join
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(SpatialJoinProcessor())

    results = pipeline.execute()

    logger.info("Partial analysis completed!")
    logger.info("This demonstrates the core spatial join concept.")

    return pipeline, results


def run_custom_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run a custom analysis with additional components."""
    logger.info("Running Custom Analysis")
    logger.info("=" * 30)

    # Load configuration
    config = PipelineConfig()
    pipeline = Pipeline("Custom Spatial Analysis", config=config)
    pipeline.load_config()

    # Add all components
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(SpatialJoinProcessor())
    pipeline.register_component(CorrelationAnalyzer())
    pipeline.register_component(CorrelationVisualizer())
    pipeline.register_component(summary_reporter)

    # Add custom analysis
    pipeline.register_component(custom_statistics)

    results = pipeline.execute()

    return pipeline, results


@pipeline_component(
    name="custom_statistics", description="Custom statistical analysis component"
)
def custom_statistics(context: dict[str, Any]) -> dict[str, Any]:
    """Custom statistical analysis component."""
    logger.info("Running Custom Statistical Analysis...")

    if "community_rental_data" in context:
        data = context["community_rental_data"]

        # Calculate additional statistics
        stats = {
            "total_communities": len(data),
            "communities_with_data": data["avg_rental_price"].notna().sum(),
            "rental_price_range": {
                "min": data["avg_rental_price"].min(),
                "max": data["avg_rental_price"].max(),
                "median": data["avg_rental_price"].median(),
            },
            "top_5_expensive": data.nlargest(5, "avg_rental_price")[
                ["community_name", "avg_rental_price"]
            ].to_dict("records"),
            "top_5_cheapest": data.nsmallest(5, "avg_rental_price")[
                ["community_name", "avg_rental_price"]
            ].to_dict("records"),
        }

        logger.info("  • Total communities: %d", stats["total_communities"])
        logger.info("  • Communities with data: %d", stats["communities_with_data"])
        logger.info(
            "  • Rental price range: $%.0f - $%.0f",
            stats["rental_price_range"]["min"],
            stats["rental_price_range"]["max"],
        )

        return {"custom_stats": stats}

    return {}


if __name__ == "__main__":
    logger.info("Spatial Data Analysis Pipeline Examples")
    logger.info("=" * 45)

    logger.info("1. Running Full Analysis...")
    pipeline1, results1 = run_full_analysis()

    logger.info("=" * 50)
    logger.info("2. Running Partial Analysis...")
    pipeline2, results2 = run_partial_analysis()

    logger.info("=" * 50)
    logger.info("3. Running Custom Analysis...")
    pipeline3, results3 = run_custom_analysis()
