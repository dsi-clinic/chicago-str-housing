"""Housing analysis components.

This package contains all housing-specific components organized by type:
- loaders: Data loading components
- processors: Data processing and transformation components
- analyzers: Statistical analysis components
- visualizers: Visualization components
- utils: Utility functions
- constants: Shared constants
"""

from housing.components.analyzers import CorrelationAnalyzer, TractAnalyzer
from housing.components.loaders import (
    CommunityBoundariesLoader,
    RentalDataLoader,
    TractBoundariesLoader,
    ZipBoundariesLoader,
)
from housing.components.processors import TractToCommunityProcessor, ZipToTractProcessor
from housing.components.utils import summary_reporter
from housing.components.visualizers import (
    CorrelationVisualizer,
    RentalDistributionVisualizer,
    RentalMapVisualizer,
)

__all__ = [
    # Loaders
    "RentalDataLoader",
    "ZipBoundariesLoader",
    "CommunityBoundariesLoader",
    "TractBoundariesLoader",
    # Processors
    "ZipToTractProcessor",
    "TractToCommunityProcessor",
    # Analyzers
    "CorrelationAnalyzer",
    "TractAnalyzer",
    # Visualizers
    "CorrelationVisualizer",
    "RentalDistributionVisualizer",
    "RentalMapVisualizer",
    # Utils
    "summary_reporter",
]
