"""Base pipeline architecture for Chicago housing analysis.

This module provides a flexible pipeline system that allows registering
different analysis components and running them in a coordinated manner.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Container for pipeline execution results."""

    component_name: str
    success: bool
    execution_time: float
    data: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PipelineComponent(ABC):
    """Abstract base class for pipeline components."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.dependencies: list[str] = []
        self.required_data: list[str] = []
        self.output_data: list[str] = []

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> Any:  # noqa: ANN401
        """Execute the component logic."""
        pass

    def validate_dependencies(self, context: dict[str, Any]) -> bool:
        """Validate that all dependencies are available in context."""
        for dep in self.dependencies:
            if dep not in context:
                logger.error(f"Missing dependency '{dep}' for component '{self.name}'")
                return False
        return True

    def validate_required_data(self, context: dict[str, Any]) -> bool:
        """Validate that all required data is available in context."""
        for data_key in self.required_data:
            if data_key not in context:
                logger.error(
                    f"Missing required data '{data_key}' for component '{self.name}'"
                )
                return False
        return True


class DataLoader(PipelineComponent):
    """Base class for data loading components."""

    def __init__(self, name: str, file_path: str, description: str = "") -> None:
        super().__init__(name, description)
        self.file_path = Path(file_path)
        self.output_data = [name]


class DataProcessor(PipelineComponent):
    """Base class for data processing components."""

    def __init__(self, name: str, description: str = "") -> None:
        super().__init__(name, description)


class Analyzer(PipelineComponent):
    """Base class for analysis components."""

    def __init__(self, name: str, description: str = "") -> None:
        super().__init__(name, description)


class Visualizer(PipelineComponent):
    """Base class for visualization components."""

    def __init__(self, name: str, description: str = "") -> None:
        super().__init__(name, description)


class Pipeline:
    """Main pipeline orchestrator."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.components: dict[str, PipelineComponent] = {}
        self.execution_order: list[str] = []
        self.context: dict[str, Any] = {}
        self.results: list[PipelineResult] = []
        self.config: dict[str, Any] = {}

    def register_component(self, component: PipelineComponent) -> None:
        """Register a component with the pipeline."""
        self.components[component.name] = component
        logger.info(f"Registered component: {component.name}")

    def register_components(self, components: list[PipelineComponent]) -> None:
        """Register multiple components at once."""
        for component in components:
            self.register_component(component)

    def set_execution_order(self, order: list[str]) -> None:
        """Set the execution order for components."""
        # Validate that all components in order are registered
        for component_name in order:
            if component_name not in self.components:
                raise ValueError(f"Component '{component_name}' not registered")
        self.execution_order = order
        logger.info(f"Set execution order: {order}")

    def auto_determine_order(self) -> list[str]:
        """Automatically determine execution order based on dependencies."""
        # Simple topological sort based on dependencies
        visited = set()
        temp_visited = set()
        order = []

        def visit(component_name: str) -> None:
            if component_name in temp_visited:
                raise ValueError(
                    f"Circular dependency detected involving '{component_name}'"
                )
            if component_name in visited:
                return

            temp_visited.add(component_name)
            component = self.components[component_name]

            # Visit dependencies first
            for dep in component.dependencies:
                if dep in self.components:
                    visit(dep)

            temp_visited.remove(component_name)
            visited.add(component_name)
            order.append(component_name)

        # Visit all components
        for component_name in self.components:
            if component_name not in visited:
                visit(component_name)

        return order

    def set_config(self, config: dict[str, Any]) -> None:
        """Set pipeline configuration."""
        self.config = config
        self.context.update(config)

    def add_to_context(self, key: str, value: Any) -> None:  # noqa: ANN401
        """Add data to the pipeline context."""
        self.context[key] = value

    def execute(self, components: list[str] | None = None) -> list[PipelineResult]:
        """Execute the pipeline or specific components."""
        if components is None:
            if not self.execution_order:
                self.execution_order = self.auto_determine_order()
            components = self.execution_order

        logger.info(f"Starting pipeline execution: {self.name}")
        logger.info(f"Components to execute: {components}")

        results = []

        for component_name in components:
            if component_name not in self.components:
                logger.error(f"Component '{component_name}' not found")
                continue

            component = self.components[component_name]
            result = self._execute_component(component)
            results.append(result)

            # Add result data to context if successful
            if result.success and result.data is not None:
                self.context[component_name] = result.data

        self.results = results
        logger.info(f"Pipeline execution completed: {self.name}")
        return results

    def _execute_component(self, component: PipelineComponent) -> PipelineResult:
        """Execute a single component."""
        start_time = time.time()

        try:
            # Validate dependencies and required data
            if not component.validate_dependencies(self.context):
                return PipelineResult(
                    component_name=component.name,
                    success=False,
                    execution_time=0,
                    error="Missing dependencies",
                )

            if not component.validate_required_data(self.context):
                return PipelineResult(
                    component_name=component.name,
                    success=False,
                    execution_time=0,
                    error="Missing required data",
                )

            # Execute the component
            logger.info(f"Executing component: {component.name}")
            data = component.execute(self.context)
            execution_time = time.time() - start_time

            return PipelineResult(
                component_name=component.name,
                success=True,
                execution_time=execution_time,
                data=data,
                metadata={"description": component.description},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing component '{component.name}': {str(e)}")

            return PipelineResult(
                component_name=component.name,
                success=False,
                execution_time=execution_time,
                error=str(e),
            )

    def get_results_summary(self) -> dict[str, Any]:
        """Get a summary of pipeline execution results."""
        total_components = len(self.results)
        successful_components = sum(1 for r in self.results if r.success)
        total_time = sum(r.execution_time for r in self.results)

        return {
            "pipeline_name": self.name,
            "total_components": total_components,
            "successful_components": successful_components,
            "failed_components": total_components - successful_components,
            "total_execution_time": total_time,
            "success_rate": successful_components / total_components
            if total_components > 0
            else 0,
            "results": [
                {
                    "component": r.component_name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "error": r.error,
                }
                for r in self.results
            ],
        }

    def save_results(self, output_path: str) -> None:
        """Save pipeline results to a file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w") as f:
            json.dump(self.get_results_summary(), f, indent=2, default=str)

        logger.info(f"Results saved to: {output_path}")


# Decorator for easy component registration
def pipeline_component(
    name: str,
    description: str = "",
    dependencies: list[str] = None,
    required_data: list[str] = None,
    output_data: list[str] = None,
) -> Callable[[Callable], PipelineComponent]:
    """Decorator to easily create pipeline components."""

    def decorator(func: Callable) -> PipelineComponent:
        class DecoratedComponent(PipelineComponent):
            def __init__(self) -> None:
                super().__init__(name, description)
                self.dependencies = dependencies or []
                self.required_data = required_data or []
                self.output_data = output_data or [name]

            def execute(self, context: dict[str, Any]) -> Any:  # noqa: ANN401
                return func(context)

        return DecoratedComponent()

    return decorator
