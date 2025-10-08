"""Example usage of the Spatial Data Analysis Pipeline.

This script demonstrates census tract-level spatial analysis:
1. Loading data from different formats (CSV with WKT geometries)
2. Spatial joins with many-to-many relationships (zip → tract)
3. Area-weighted aggregation across boundaries
4. Statistical analysis on tract-level datasets

This demonstrates the most challenging aspects of spatial data analysis.
"""

import logging
from typing import Any

from pipeline import (
    CommunityBoundariesLoader,
    CorrelationAnalyzer,
    Pipeline,
    PipelineResult,
    RentalDataLoader,
    TractAnalyzer,
    TractBoundariesLoader,
    TractToCommunityProcessor,
    ZipBoundariesLoader,
    ZipToTractProcessor,
    pipeline_component,
)
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


def create_tract_analysis_pipeline() -> Pipeline:
    """Create a pipeline for census tract-level analysis."""
    # Load configuration
    config = PipelineConfig()
    pipeline = Pipeline("Census Tract Analysis", config=config)
    pipeline.load_config()

    # Step 1: Load data sources
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())

    # Step 2: Perform spatial join (zip → tract with area weighting)
    pipeline.register_component(ZipToTractProcessor())

    # Step 3: Analyze at tract level
    pipeline.register_component(TractAnalyzer())

    return pipeline


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the complete tract-level analysis pipeline."""
    logger.info("Starting Census Tract Analysis Pipeline")
    logger.info("=" * 50)

    pipeline = create_tract_analysis_pipeline()
    results = pipeline.execute()

    logger.info("Pipeline execution completed!")
    logger.info("Generated %d results:", len(results))
    for result in results:
        status = "SUCCESS" if result.success else "FAILED"
        logger.info("  • %s: %s", result.component_name, status)

    # Show key results
    if "zip_to_tract_crosswalk" in pipeline.context:
        crosswalk = pipeline.context["zip_to_tract_crosswalk"]
        logger.info("\nCrosswalk created: %d zip-tract mappings", len(crosswalk))

    if "tract_rental_data" in pipeline.context:
        tract_data = pipeline.context["tract_rental_data"]
        logger.info("Tract data: %d tracts analyzed", len(tract_data))

    return pipeline, results


def run_partial_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run only the data loading and spatial join (no analysis)."""
    logger.info("Running Partial Analysis (Data Loading + Spatial Join)")
    logger.info("=" * 55)

    config = PipelineConfig()
    pipeline = Pipeline("Partial Tract Analysis", config=config)
    pipeline.load_config()

    # Only load data and perform spatial join
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipToTractProcessor())

    results = pipeline.execute()

    logger.info("Partial analysis completed!")
    logger.info("This demonstrates the zip-to-tract spatial join.")

    return pipeline, results


def run_hierarchical_aggregation() -> tuple[Pipeline, list[PipelineResult]]:
    """Demonstrate hierarchical aggregation: Zip → Tract → Community."""
    logger.info("Running Hierarchical Aggregation Analysis")
    logger.info("=" * 50)
    logger.info("Workflow: Zip codes → Census tracts → Community areas")

    config = PipelineConfig()
    pipeline = Pipeline("Hierarchical Aggregation", config=config)
    pipeline.load_config()

    # Step 1: Load all boundaries
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())

    # Step 2: Zip → Tract aggregation
    pipeline.register_component(ZipToTractProcessor())

    # Step 3: Tract → Community aggregation (the clean way!)
    pipeline.register_component(TractToCommunityProcessor())

    # Step 4: Analyze at both levels
    pipeline.register_component(TractAnalyzer())
    pipeline.register_component(CorrelationAnalyzer())

    results = pipeline.execute()

    # Show comparison
    if (
        "tract_rental_data" in pipeline.context
        and "community_rental_data" in pipeline.context
    ):
        tract_data = pipeline.context["tract_rental_data"]
        community_data = pipeline.context["community_rental_data"]

        logger.info("\n=== Multi-Level Analysis Results ===")
        logger.info(
            "Tract level: %d areas with data",
            tract_data["avg_rental_price"].notna().sum(),
        )
        logger.info(
            "Community level: %d areas with data",
            community_data["avg_rental_price"].notna().sum(),
        )
        logger.info(
            "Granularity increase: %.1fx more detail at tract level",
            tract_data["avg_rental_price"].notna().sum()
            / community_data["avg_rental_price"].notna().sum(),
        )

    return pipeline, results


def run_custom_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run tract analysis with custom statistics component."""
    logger.info("Running Custom Tract Analysis")
    logger.info("=" * 30)

    config = PipelineConfig()
    pipeline = Pipeline("Custom Tract Analysis", config=config)
    pipeline.load_config()

    # Add standard components
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TractAnalyzer())

    # Add custom analysis
    pipeline.register_component(custom_tract_statistics)

    results = pipeline.execute()

    return pipeline, results


@pipeline_component(
    name="custom_tract_statistics", description="Custom tract-level statistics"
)
def custom_tract_statistics(context: dict[str, Any]) -> dict[str, Any]:
    """Custom statistical analysis for tract data."""
    logger.info("Running Custom Tract Statistics...")

    if "tract_rental_data" in context:
        data = context["tract_rental_data"]

        # Calculate additional statistics
        stats = {
            "total_tracts": len(data),
            "tracts_with_data": data["avg_rental_price"].notna().sum(),
            "rental_price_range": {
                "min": data["avg_rental_price"].min(),
                "max": data["avg_rental_price"].max(),
                "median": data["avg_rental_price"].median(),
            },
            "top_5_expensive_tracts": data.nlargest(5, "avg_rental_price")[
                ["tract_geoid", "avg_rental_price"]
            ].to_dict("records"),
            "top_5_cheapest_tracts": data.nsmallest(5, "avg_rental_price")[
                ["tract_geoid", "avg_rental_price"]
            ].to_dict("records"),
        }

        logger.info("  • Total tracts: %d", stats["total_tracts"])
        logger.info("  • Tracts with data: %d", stats["tracts_with_data"])
        logger.info(
            "  • Rental price range: $%.0f - $%.0f",
            stats["rental_price_range"]["min"],
            stats["rental_price_range"]["max"],
        )

        return {"custom_tract_stats": stats}

    return {}


if __name__ == "__main__":
    logger.info("Census Tract Analysis Pipeline Examples")
    logger.info("=" * 45)

    logger.info("\n1. Running Full Tract Analysis...")
    pipeline1, results1 = run_full_analysis()

    logger.info("\n%s", "=" * 50)
    logger.info("2. Running Hierarchical Aggregation (Zip → Tract → Community)...")
    pipeline2, results2 = run_hierarchical_aggregation()

    logger.info("\n%s", "=" * 50)
    logger.info("3. Running Partial Analysis...")
    pipeline3, results3 = run_partial_analysis()

    logger.info("\n" + "=" * 50)
    logger.info("4. Running Custom Analysis...")
    pipeline4, results4 = run_custom_analysis()
