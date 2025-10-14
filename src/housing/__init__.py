"""Chicago Housing Analysis Package.

This package contains housing-specific components for spatial data analysis
of Chicago rental prices and geographic boundaries.

Components are organized into subdirectories:
- components/loaders: Data loading components
- components/processors: Spatial processing components
- components/analyzers: Statistical analysis components
- components/visualizers: Visualization components
"""

from housing.components import (
    AirbnbToTractProcessor,
    CommunityBoundariesLoader,
    CorrelationAnalyzer,
    CorrelationVisualizer,
    PointsToTractProcessor,
    RentalDataLoader,
    RentalDistributionVisualizer,
    RentalMapVisualizer,
    TractAnalyzer,
    TractBoundariesLoader,
    TractToCommunityProcessor,
    ZipBoundariesLoader,
    ZipToTractProcessor,
    summary_reporter,
)

__all__ = [
    "RentalDataLoader",
    "ZipBoundariesLoader",
    "CommunityBoundariesLoader",
    "TractBoundariesLoader",
    "ZipToTractProcessor",
    "TractToCommunityProcessor",
    "PointsToTractProcessor",
    "AirbnbToTractProcessor",
    "CorrelationAnalyzer",
    "TractAnalyzer",
    "CorrelationVisualizer",
    "RentalDistributionVisualizer",
    "RentalMapVisualizer",
    "summary_reporter",
]
