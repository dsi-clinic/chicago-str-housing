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
    TractAnalyzer,
    TractBoundariesLoader,
    TractToCommunityProcessor,
    ZipBoundariesLoader,
    ZipToTractProcessor,
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
    # Components
    "RentalDataLoader",
    "ZipBoundariesLoader",
    "CommunityBoundariesLoader",
    "TractBoundariesLoader",
    "ZipToTractProcessor",
    "TractToCommunityProcessor",
    "CorrelationAnalyzer",
    "TractAnalyzer",
    "CorrelationVisualizer",
    "summary_reporter",
]
