"""Chicago Housing Analysis Pipeline

A flexible pipeline system for registering and executing different analysis components.
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
from pipeline.components import (
    CommunityBoundariesLoader,
    CommunityRentalProcessor,
    CorrelationAnalyzer,
    CorrelationVisualizer,
    HouseShareDataLoader,
    HouseShareMerger,
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
    # Concrete components
    "RentalDataLoader",
    "ZipBoundariesLoader",
    "CommunityBoundariesLoader",
    "HouseShareDataLoader",
    "SpatialJoinProcessor",
    "CommunityRentalProcessor",
    "HouseShareMerger",
    "CorrelationAnalyzer",
    "CorrelationVisualizer",
    "summary_reporter",
]
