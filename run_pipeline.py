#!/usr/bin/env python3
"""Main script to run the Chicago Housing Analysis Pipeline.

Usage:
    python run_pipeline.py [--config CONFIG_PATH] [--components COMPONENT1,COMPONENT2] [--output OUTPUT_DIR]
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.pipeline import (
    CommunityBoundariesLoader,
    CommunityRentalProcessor,
    CorrelationAnalyzer,
    CorrelationVisualizer,
    HouseShareDataLoader,
    HouseShareMerger,
    Pipeline,
    RentalDataLoader,
    SpatialJoinProcessor,
    ZipBoundariesLoader,
    summary_reporter,
)
from src.pipeline.config import load_pipeline_config


def create_pipeline_from_config(config_path: str = None) -> Pipeline:
    """Create pipeline from configuration file."""
    # Load configuration
    config = load_pipeline_config(config_path)

    # Create pipeline
    pipeline = Pipeline(name=config.name, description=config.description)

    # Register all components
    components = [
        # Data loaders
        RentalDataLoader(config.data.rental_data_path),
        ZipBoundariesLoader(config.data.zip_boundaries_path),
        CommunityBoundariesLoader(config.data.community_boundaries_path),
        HouseShareDataLoader(config.data.house_share_data_path),
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

    # Set execution order if specified
    if config.execution_order:
        pipeline.set_execution_order(config.execution_order)

    # Set configuration
    config_dict = {
        "output_dir": config.output.output_dir,
        "save_intermediate_results": config.output.save_intermediate_results,
        "save_plots": config.output.save_plots,
        "plot_format": config.output.plot_format,
        "plot_dpi": config.output.plot_dpi,
        "recent_months": config.analysis.recent_months,
        "correlation_threshold": config.analysis.correlation_threshold,
    }
    pipeline.set_config(config_dict)

    return pipeline


def main() -> int | None:
    """Main function to run the pipeline."""
    parser = argparse.ArgumentParser(
        description="Run Chicago Housing Analysis Pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="/project/config/pipeline_config.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--components",
        type=str,
        help="Comma-separated list of components to run (optional)",
    )
    parser.add_argument(
        "--output", type=str, help="Output directory (overrides config)"
    )
    parser.add_argument(
        "--list-components",
        action="store_true",
        help="List all available components and exit",
    )

    args = parser.parse_args()

    try:
        # Create pipeline
        pipeline = create_pipeline_from_config(args.config)

        # Override output directory if specified
        if args.output:
            pipeline.add_to_context("output_dir", args.output)

        # List components if requested
        if args.list_components:
            print("Available components:")
            for name, component in pipeline.components.items():
                print(f"  - {name}: {component.description}")
            return

        # Determine which components to run
        components_to_run = None
        if args.components:
            components_to_run = [c.strip() for c in args.components.split(",")]
            # Validate components exist
            for component in components_to_run:
                if component not in pipeline.components:
                    print(f"Error: Component '{component}' not found")
                    print("Available components:")
                    for name in pipeline.components.keys():
                        print(f"  - {name}")
                    return 1

        # Run the pipeline
        print("=" * 60)
        print("CHICAGO HOUSING ANALYSIS PIPELINE")
        print("=" * 60)
        print(f"Pipeline: {pipeline.name}")
        print(f"Description: {pipeline.description}")

        if components_to_run:
            print(f"Running components: {', '.join(components_to_run)}")
        else:
            print("Running all components")

        print("-" * 60)

        # Execute pipeline
        results = pipeline.execute(components_to_run)

        # Print results summary
        summary = pipeline.get_results_summary()
        print("\nPipeline Execution Summary:")
        print(f"- Total components: {summary['total_components']}")
        print(f"- Successful: {summary['successful_components']}")
        print(f"- Failed: {summary['failed_components']}")
        print(f"- Success rate: {summary['success_rate']:.1%}")
        print(f"- Total execution time: {summary['total_execution_time']:.2f} seconds")

        # Print individual component results
        print("\nComponent Results:")
        for result in results:
            status = "✓" if result.success else "✗"
            print(f"{status} {result.component_name}: {result.execution_time:.2f}s")
            if not result.success and result.error:
                print(f"    Error: {result.error}")

        # Save results
        output_dir = pipeline.context.get("output_dir", "/project/output")
        results_path = Path(output_dir) / "pipeline_results.json"
        pipeline.save_results(str(results_path))
        print(f"\nResults saved to: {results_path}")

        # Return appropriate exit code
        return 0 if summary["failed_components"] == 0 else 1

    except Exception as e:
        print(f"Error running pipeline: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
