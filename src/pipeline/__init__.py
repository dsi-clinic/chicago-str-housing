"""Spatial Data Analysis Pipeline"""

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
from pipeline.components import (
    CommunityBoundariesLoader,
    CorrelationAnalyzer,
    CorrelationVisualizer,
    RentalDataLoader,
    SpatialJoinProcessor,
    ZipBoundariesLoader,
    summary_reporter,
)

__all__ = [
    # Base classes
    "Pipeline",
    "PipelineComponent",
    "DataLoader",
    "DataProcessor",
    "Analyzer",
    "Visualizer",
    "PipelineResult",
    "pipeline_component",
    # Core educational components
    "RentalDataLoader",
    "ZipBoundariesLoader",
    "CommunityBoundariesLoader",
    "SpatialJoinProcessor",
    "CorrelationAnalyzer",
    "CorrelationVisualizer",
    "summary_reporter",
]
