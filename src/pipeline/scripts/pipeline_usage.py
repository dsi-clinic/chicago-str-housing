"""Generic Pipeline Framework Demo.

This script demonstrates how to use the abstract pipeline framework
with simple example components. This is a minimal demo showing:
1. Creating custom pipeline components
2. Registering components with a pipeline
3. Executing the pipeline
4. Accessing results

For a complete real-world example, see: src/housing/scripts/housing_eda_pipeline.py
"""

import logging
from typing import Any

from pipeline import (
    Analyzer,
    DataLoader,
    DataProcessor,
    Pipeline,
    PipelineResult,
    Visualizer,
    pipeline_component,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE COMPONENTS
# ============================================================================


class ExampleDataLoader(DataLoader):
    """Example data loader component."""

    def __init__(self) -> None:
        """Initialize the example data loader."""
        super().__init__(
            "example_loader",
            "/project/data/example.csv",
            "Load example data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load example data."""
        logger.info("Loading example data...")

        # Simulate loading data
        data = {
            "values": [1, 2, 3, 4, 5],
            "labels": ["A", "B", "C", "D", "E"],
        }

        logger.info("Loaded %d records", len(data["values"]))
        return {"example_data": data}


class ExampleProcessor(DataProcessor):
    """Example data processor component."""

    def __init__(self) -> None:
        """Initialize the example processor."""
        super().__init__(
            "example_processor",
            "Process example data",
        )
        self.required_data = ["example_data"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Process example data."""
        logger.info("Processing example data...")

        data = context["example_data"]

        # Simulate processing - double all values
        processed = {
            "values": [v * 2 for v in data["values"]],
            "labels": data["labels"],
        }

        logger.info("Processed %d records", len(processed["values"]))
        return {"processed_data": processed}


class ExampleAnalyzer(Analyzer):
    """Example analyzer component."""

    def __init__(self) -> None:
        """Initialize the example analyzer."""
        super().__init__(
            "example_analyzer",
            "Analyze processed data",
        )
        self.required_data = ["processed_data"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze processed data."""
        logger.info("Analyzing processed data...")

        data = context["processed_data"]

        # Calculate statistics
        values = data["values"]
        stats = {
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

        logger.info("Analysis complete:")
        logger.info("  Mean: %.2f", stats["mean"])
        logger.info("  Range: %d - %d", stats["min"], stats["max"])

        return {"analysis_results": stats}


class ExampleVisualizer(Visualizer):
    """Example visualizer component."""

    def __init__(self) -> None:
        """Initialize the example visualizer."""
        super().__init__(
            "example_visualizer",
            "Visualize analysis results",
        )
        self.required_data = ["analysis_results"]

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Visualize analysis results."""
        logger.info("Creating visualizations...")

        stats = context["analysis_results"]

        # Simulate creating a visualization
        logger.info("Visualization created with:")
        logger.info("  %d data points", stats["count"])
        logger.info("  Mean value: %.2f", stats["mean"])

        return {"visualization_created": True}


# ============================================================================
# PIPELINE CREATION AND EXECUTION
# ============================================================================


def create_simple_pipeline() -> Pipeline:
    """Create a simple demo pipeline."""
    pipeline = Pipeline("Simple Demo Pipeline")

    # Register components in order
    pipeline.register_component(ExampleDataLoader())
    pipeline.register_component(ExampleProcessor())
    pipeline.register_component(ExampleAnalyzer())
    pipeline.register_component(ExampleVisualizer())

    return pipeline


def create_pipeline_with_decorator() -> Pipeline:
    """Create a pipeline using the decorator pattern."""
    pipeline = Pipeline("Decorator Demo Pipeline")

    # Register standard components
    pipeline.register_component(ExampleDataLoader())
    pipeline.register_component(ExampleProcessor())

    # Register decorator-based component
    pipeline.register_component(custom_reporter)

    return pipeline


@pipeline_component(
    name="custom_reporter",
    description="Custom reporter using decorator",
    required_data=["processed_data"],
)
def custom_reporter(context: dict[str, Any]) -> dict[str, Any]:
    """Custom reporter component created with decorator."""
    logger.info("Running custom reporter...")

    data = context["processed_data"]

    print("\n" + "=" * 50)
    print("CUSTOM REPORT")
    print("=" * 50)
    print(f"Processed {len(data['values'])} records")
    print(f"Values: {data['values']}")
    print(f"Labels: {data['labels']}")
    print("=" * 50 + "\n")

    return {"report_generated": True}


def run_simple_demo() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the simple pipeline demo."""
    logger.info("=" * 60)
    logger.info("SIMPLE PIPELINE DEMO")
    logger.info("=" * 60)

    pipeline = create_simple_pipeline()
    results = pipeline.execute()

    logger.info("\nPipeline completed!")
    logger.info("Executed %d components", len(results))

    # Show results summary
    summary = pipeline.get_results_summary()
    logger.info("Success rate: %.1f%%", summary["success_rate"] * 100)

    return pipeline, results


def run_decorator_demo() -> tuple[Pipeline, list[PipelineResult]]:
    """Run the decorator-based pipeline demo."""
    logger.info("\n" + "=" * 60)
    logger.info("DECORATOR PATTERN DEMO")
    logger.info("=" * 60)

    pipeline = create_pipeline_with_decorator()
    results = pipeline.execute()

    logger.info("\nPipeline completed!")

    return pipeline, results


def main() -> None:
    """Run all demo pipelines."""
    logger.info("GENERIC PIPELINE FRAMEWORK DEMO")
    logger.info("This demonstrates the abstract pipeline framework.")
    logger.info(
        "For a real-world example, see: housing/scripts/housing_eda_pipeline.py"
    )
    logger.info("")

    # Run demos
    pipeline1, results1 = run_simple_demo()
    pipeline2, results2 = run_decorator_demo()

    logger.info("\n" + "=" * 60)
    logger.info("ALL DEMOS COMPLETED")
    logger.info("=" * 60)
    logger.info("Total pipelines executed: 2")
    logger.info("Total components executed: %d", len(results1) + len(results2))


if __name__ == "__main__":
    main()
