"""Chicago Housing Analysis Package.

This package contains housing-specific components for spatial data analysis
of Chicago rental prices and geographic boundaries.

Components are organized into subdirectories:
- components/loaders: Data loading components
- components/processors: Spatial processing components
- components/analyzers: Statistical analysis components
- components/visualizers: Visualization components
"""

# Direct imports - no need to manage __init__.py files!
from housing.components.analyzers.rental_tract import RentalTractAnalyzer
from housing.components.analyzers.str_prohibition import STRProhibitionAnalyzer
from housing.components.loaders.airbnb_data import AirbnbDataLoader
from housing.components.loaders.city_boundaries import CityBoundariesLoader
from housing.components.loaders.community_boundaries import CommunityBoundariesLoader
from housing.components.loaders.foreclosed_data import ForeclosedDataLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.processors.points_to_tract import PointsToTractProcessor
from housing.components.processors.tract_to_community import TractToCommunityProcessor
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.visualizers.airbnb_distribution import (
    AirbnbDistributionVisualizer,
)
from housing.components.visualizers.airbnb_map import AirbnbMapVisualizer
from housing.components.visualizers.foreclosed_distribution import (
    ForeclosedDistributionVisualizer,
)
from housing.components.visualizers.foreclosed_map import ForeclosedMapVisualizer
from housing.components.visualizers.rental_distribution import (
    RentalDistributionVisualizer,
)
from housing.components.visualizers.rental_map import RentalMapVisualizer
from housing.components.visualizers.str_distribution import STRDistributionVisualizer
from housing.components.visualizers.str_map import STRMapVisualizer
from housing.components.visualizers.str_prohibition_viz import STRProhibitionVisualizer

__all__ = [
    "AirbnbDataLoader",
    "AirbnbDistributionVisualizer",
    "AirbnbMapVisualizer",
    "CityBoundariesLoader",
    "CommunityBoundariesLoader",
    "ForeclosedDataLoader",
    "ForeclosedDistributionVisualizer",
    "ForeclosedMapVisualizer",
    "PointsToTractProcessor",
    "RentalDataLoader",
    "RentalDistributionVisualizer",
    "RentalMapVisualizer",
    "RentalTractAnalyzer",
    "STRDistributionVisualizer",
    "STRMapVisualizer",
    "STRProhibitionAnalyzer",
    "STRProhibitionDataLoader",
    "STRProhibitionVisualizer",
    "TractBoundariesLoader",
    "TractToCommunityProcessor",
    "ZipBoundariesLoader",
    "ZipToTractProcessor",
]
