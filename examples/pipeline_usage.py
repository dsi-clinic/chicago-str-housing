"""Example usage of the Spatial Data Analysis Pipeline.

This script demonstrates the core spatial data analysis concepts:
1. Loading data from different formats (CSV, GeoJSON)
2. Spatial joins and geometry transformations
3. Aggregating data across spatial boundaries
4. Statistical analysis on merged datasets

This is designed for educational use to teach students the most challenging
aspects of spatial data analysis.
"""

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


def create_spatial_analysis_pipeline() -> Pipeline:
    """Create a pipeline that demonstrates core spatial data analysis concepts."""
    pipeline = Pipeline("Spatial Data Analysis Demo")

    # Step 1: Load data from different sources
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
    print("Starting Spatial Data Analysis Pipeline")
    print("=" * 50)

    pipeline = create_spatial_analysis_pipeline()
    results = pipeline.execute()

    print("\nPipeline execution completed!")
    print(f"Generated {len(results)} results:")
    for result in results:
        status = "SUCCESS" if result.success else "FAILED"
        print(f"  • {result.component_name}: {status}")

    return pipeline, results


def run_partial_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run only the data loading and spatial join parts."""
    print("Running Partial Analysis (Data Loading + Spatial Join)")
    print("=" * 55)

    pipeline = Pipeline("Partial Spatial Analysis")

    # Only load data and perform spatial join
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(CommunityBoundariesLoader())
    pipeline.register_component(SpatialJoinProcessor())

    results = pipeline.execute()

    print("\nPartial analysis completed!")
    print("This demonstrates the core spatial join concept.")

    return pipeline, results


def run_custom_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run a custom analysis with additional components."""
    print("Running Custom Analysis")
    print("=" * 30)

    pipeline = Pipeline("Custom Spatial Analysis")

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
    print("Running Custom Statistical Analysis...")

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

        print(f"  • Total communities: {stats['total_communities']}")
        print(f"  • Communities with data: {stats['communities_with_data']}")
        print(
            f"  • Rental price range: ${stats['rental_price_range']['min']:,.0f} - ${stats['rental_price_range']['max']:,.0f}"
        )

        return {"custom_stats": stats}

    return {}


if __name__ == "__main__":
    print("Spatial Data Analysis Pipeline Examples")
    print("=" * 45)

    print("\n1. Running Full Analysis...")
    pipeline1, results1 = run_full_analysis()

    print("\n" + "=" * 50)
    print("\n2. Running Partial Analysis...")
    pipeline2, results2 = run_partial_analysis()

    print("\n" + "=" * 50)
    print("\n3. Running Custom Analysis...")
    pipeline3, results3 = run_custom_analysis()
