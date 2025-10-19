# Housing Components Structure

## Overview

The housing components have been organized into a modular directory structure where each component lives in its own file. This makes it easy for contributors to work independently on different components without merge conflicts.

## New Directory Structure

```
src/housing/
├── __init__.py                          # Main package exports (uses direct imports)
├── components/
│   ├── constants.py                     # Shared constants
│   ├── utils.py                         # Utility functions
│   │
│   ├── loaders/                         # DATA LOADERS
│   │   ├── rental_data.py               # RentalDataLoader
│   │   ├── zip_boundaries.py            # ZipBoundariesLoader
│   │   ├── community_boundaries.py      # CommunityBoundariesLoader
│   │   ├── tract_boundaries.py          # TractBoundariesLoader
│   │   ├── airbnb_data.py               # AirbnbDataLoader
│   │   ├── str_prohibition_data.py      # STRProhibitionDataLoader
│   │   └── city_boundaries.py           # CityBoundariesLoader
│   │
│   ├── processors/                      # DATA PROCESSORS
│   │   ├── zip_to_tract.py              # ZipToTractProcessor
│   │   ├── tract_to_community.py        # TractToCommunityProcessor
│   │   └── points_to_tract.py           # PointsToTractProcessor
│   │
│   ├── analyzers/                       # ANALYZERS
│   │   ├── rental_correlation.py       # RentalCorrelationAnalyzer
│   │   ├── rental_tract.py             # RentalTractAnalyzer
│   │   └── str_prohibition.py          # STRProhibitionAnalyzer
│   │
│   └── visualizers/                     # VISUALIZERS
│       ├── rental_correlation.py       # RentalCorrelationVisualizer
│       ├── rental_distribution.py      # RentalDistributionVisualizer
│       ├── rental_map.py               # RentalMapVisualizer
│       ├── airbnb_distribution.py      # AirbnbDistributionVisualizer
│       ├── airbnb_map.py               # AirbnbMapVisualizer
│       ├── str_distribution.py         # STRDistributionVisualizer
│       ├── str_map.py                  # STRMapVisualizer
│       └── str_prohibition_viz.py      # STRProhibitionVisualizer
│
└── scripts/
    └── housing_eda_pipeline.py          # Main housing pipeline
```

## Component Organization

### `components/loaders/`
Each data loader gets its own file:
- **`rental_data.py`** - Loads ZORI rental price data
- **`zip_boundaries.py`** - Loads zip code boundaries
- **`community_boundaries.py`** - Loads community area boundaries
- **`tract_boundaries.py`** - Loads census tract boundaries
- **`airbnb_data.py`** - Loads Airbnb listing data
- **`str_prohibition_data.py`** - Loads STR prohibition data
- **`city_boundaries.py`** - Loads Chicago city boundaries

### `components/processors/`
Spatial processing components:
- **`zip_to_tract.py`** - Transforms data from zip to tract level
- **`tract_to_community.py`** - Aggregates tract data to community level
- **`points_to_tract.py`** - Aggregates point data to census tracts

### `components/analyzers/`
Statistical analysis components:
- **`rental_correlation.py`** - Community-level correlation analysis
- **`rental_tract.py`** - Tract-level analysis
- **`str_prohibition.py`** - STR prohibition density analysis

### `components/visualizers/`
Visualization components:
- **`rental_correlation.py`** - Creates correlation visualizations
- **`rental_distribution.py`** - Rental price distribution plots
- **`rental_map.py`** - Rental price spatial maps
- **`airbnb_distribution.py`** - Airbnb distribution plots
- **`airbnb_map.py`** - Airbnb spatial maps
- **`str_distribution.py`** - STR prohibition distribution plots
- **`str_map.py`** - STR prohibition spatial maps
- **`str_prohibition_viz.py`** - STR prohibition correlation charts

### `components/constants.py`
Shared constants used across components:
- Correlation thresholds
- Analysis parameters

### `components/utils.py`
Utility functions:
- Reserved for future utility functions that might be needed across components

## Import Patterns

### Direct Imports (Recommended)
The project now uses direct imports instead of managing `__init__.py` files:

```python
# In pipeline scripts - direct imports
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.analyzers.str_prohibition import STRProhibitionAnalyzer
from housing.components.visualizers.rental_map import RentalMapVisualizer

# Or import from main housing package
from housing import RentalDataLoader, STRProhibitionAnalyzer
```

### Component File Structure
```python
# In a loader file (e.g., loaders/rental_data.py)
from pipeline.base import DataLoader
import pandas as pd
import logging

class RentalDataLoader(DataLoader):
    ...
```

```python
# In an analyzer file (e.g., analyzers/str_prohibition.py)
from pipeline.base import Analyzer
from housing.components.constants import CORRELATION_STRONG_THRESHOLD

class STRProhibitionAnalyzer(Analyzer):
    ...
```