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
    STRDataLoader,
    TractBoundariesLoader,
    ZipBoundariesLoader,
)
from housing.components.processors import (
    AirbnbToTractProcessor,
    PointsToTractProcessor,
    TractToCommunityProcessor,
    ZipToTractProcessor,
)
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
    "STRDataLoader",
    # Processors
    "ZipToTractProcessor",
    "TractToCommunityProcessor",
    "PointsToTractProcessor",
    "AirbnbToTractProcessor",
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
