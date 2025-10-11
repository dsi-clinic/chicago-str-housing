"""Generic Pipeline Framework.

This module provides the abstract base classes and infrastructure for building
data analysis pipelines. It's domain-agnostic and can be used for any type
of data processing workflow.
"""

from pipeline.base import (
    Analyzer,
    DataLoader,
    DataProcessor,
    Pipeline,
    PipelineComponent,
    PipelineResult,
    Visualizer,
    pipeline_component,
)

__all__ = [
    # Core pipeline classes
    "Pipeline",
    "PipelineComponent",
    "PipelineResult",
    # Base component types
    "DataLoader",
    "DataProcessor",
    "Analyzer",
    "Visualizer",
    # Utilities
    "pipeline_component",
]
