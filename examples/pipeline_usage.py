"""Example usage of the Chicago Housing Analysis Pipeline.

This script demonstrates how to:
1. Create a pipeline
2. Register components
3. Execute the pipeline
4. View results
"""

from typing import Any

from src.pipeline import (
    CommunityBoundariesLoader,
    CommunityRentalProcessor,
    CorrelationAnalyzer,
    CorrelationVisualizer,
    HouseShareDataLoader,
    HouseShareMerger,
    Pipeline,
    PipelineResult,
    RentalDataLoader,
    SpatialJoinProcessor,
    ZipBoundariesLoader,
    summary_reporter,
)


def create_housing_analysis_pipeline() -> Pipeline:
    """Create and configure the housing analysis pipeline."""
    # Create the main pipeline
    pipeline = Pipeline(
        name="Chicago Housing Analysis",
        description="Analyze rental prices and house share prohibitions in Chicago",
    )

    # Register all components
    components = [
        # Data loaders
        RentalDataLoader(),
        ZipBoundariesLoader(),
        CommunityBoundariesLoader(),
        HouseShareDataLoader(),
        # Data processors
        SpatialJoinProcessor(),
        CommunityRentalProcessor(),
        HouseShareMerger(),
        # Analyzers
        CorrelationAnalyzer(),
        # Visualizers
        CorrelationVisualizer(),
        # Reporters
        summary_reporter,
    ]

    pipeline.register_components(components)

    # Set execution order (optional - pipeline can auto-determine based on dependencies)
    execution_order = [
        "rental_data",
        "zip_boundaries",
        "community_boundaries",
        "house_share_data",
        "spatial_join",
        "community_rental_processor",
        "house_share_merger",
        "correlation_analyzer",
        "correlation_visualizer",
        "summary_reporter",
    ]

    pipeline.set_execution_order(execution_order)

    return pipeline


def run_full_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the complete housing analysis pipeline."""
    print("=" * 60)
    print("CHICAGO HOUSING ANALYSIS PIPELINE")
    print("=" * 60)

    # Create the pipeline
    pipeline = create_housing_analysis_pipeline()

    # Set any configuration
    config = {"output_dir": "/project/output", "save_intermediate_results": True}
    pipeline.set_config(config)

    # Execute the pipeline
    results = pipeline.execute()

    # Print summary
    summary = pipeline.get_results_summary()
    print("\nPipeline Execution Summary:")
    print(f"- Total components: {summary['total_components']}")
    print(f"- Successful: {summary['successful_components']}")
    print(f"- Failed: {summary['failed_components']}")
    print(f"- Success rate: {summary['success_rate']:.1%}")
    print(f"- Total execution time: {summary['total_execution_time']:.2f} seconds")

    # Save results
    pipeline.save_results("/project/output/pipeline_results.json")

    return pipeline, results


def run_partial_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Run only specific components of the pipeline."""
    print("=" * 60)
    print("PARTIAL PIPELINE EXECUTION EXAMPLE")
    print("=" * 60)

    # Create the pipeline
    pipeline = create_housing_analysis_pipeline()

    # Run only data loading and basic processing
    partial_components = [
        "rental_data",
        "zip_boundaries",
        "community_boundaries",
        "spatial_join",
    ]

    results = pipeline.execute(components=partial_components)

    print("\nPartial execution completed:")
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"{status} {result.component_name}: {result.execution_time:.2f}s")

    return pipeline, results


def run_custom_analysis() -> tuple[Pipeline, list[PipelineResult]]:
    """Example of running a custom analysis with additional components."""
    print("=" * 60)
    print("CUSTOM ANALYSIS EXAMPLE")
    print("=" * 60)

    # Create the pipeline
    pipeline = create_housing_analysis_pipeline()

    # Add custom component using decorator
    from src.pipeline.base import pipeline_component

    @pipeline_component(
        name="custom_statistics",
        description="Calculate custom statistics",
        dependencies=["correlation_analyzer"],
        required_data=["correlation_results"],
    )
    def custom_statistics(context: dict[str, Any]) -> dict[str, Any]:
        """Calculate custom statistics."""
        correlation_results = context["correlation_results"]

        # Calculate some custom metrics
        correlations = correlation_results["correlations"]

        # Find the strongest correlation
        strongest_corr = max(correlations.items(), key=lambda x: abs(x[1]))

        print(f"Strongest correlation: {strongest_corr[0]} = {strongest_corr[1]:.3f}")

        return {
            "strongest_correlation": {
                "metric": strongest_corr[0],
                "value": strongest_corr[1],
            }
        }

    # Register the custom component
    pipeline.register_component(custom_statistics)

    # Run the analysis including the custom component
    results = pipeline.execute()

    return pipeline, results


if __name__ == "__main__":
    # Example 1: Run full analysis
    print("Example 1: Full Analysis")
    pipeline1, results1 = run_full_analysis()

    print("\n" + "=" * 60 + "\n")

    # Example 2: Run partial analysis
    print("Example 2: Partial Analysis")
    pipeline2, results2 = run_partial_analysis()

    print("\n" + "=" * 60 + "\n")

    # Example 3: Run custom analysis
    print("Example 3: Custom Analysis")
    pipeline3, results3 = run_custom_analysis()
