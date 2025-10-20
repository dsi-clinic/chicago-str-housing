"""Housing analysis components.

This package contains all housing-specific components organized by type:
- loaders: Data loading components
- processors: Data processing and transformation components
- analyzers: Statistical analysis components
- visualizers: Visualization components
- utils: Utility functions
- constants: Shared constants
"""

from housing.components.analyzers import (
    ACSTractAnalyzer,
    CorrelationAnalyzer,
    TractAnalyzer,
)
from housing.components.loaders import (
    ACSLoader,
    CommunityBoundariesLoader,
    RentalDataLoader,
    TractBoundariesLoader,
    ZipBoundariesLoader,
)
from housing.components.processors import (
    ACSToTractProcessor,
    AirbnbToTractProcessor,
    PointsToTractProcessor,
    TractToCommunityProcessor,
    ZipToTractProcessor,
)
from housing.components.utils import summary_reporter
from housing.components.visualizers import (
    ACSCorrelationVisualizer,
    ACSIncomeVisualizer,
    ACSMapVisualizer,
    CorrelationVisualizer,
    RentalDistributionVisualizer,
    RentalMapVisualizer,
)

__all__ = [
    # Loaders
    "ACSLoader",
    "RentalDataLoader",
    "ZipBoundariesLoader",
    "CommunityBoundariesLoader",
    "TractBoundariesLoader",
    # Processors
    "ACSToTractProcessor",
    "ZipToTractProcessor",
    "TractToCommunityProcessor",
    "PointsToTractProcessor",
    "AirbnbToTractProcessor",
    # Analyzers
    "ACSTractAnalyzer", 
    "CorrelationAnalyzer",
    "TractAnalyzer",
    # Visualizers
    "ACSMapVisualizer",
    "ACSIncomeVisualizer", 
    "ACSCorrelationVisualizer", 
    "CorrelationVisualizer",
    "RentalDistributionVisualizer",
    "RentalMapVisualizer",
    # Utils
    "summary_reporter",
]
