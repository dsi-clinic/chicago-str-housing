# Housing Components Structure

## Overview

The housing components have been organized into a modular directory structure where each component lives in its own file. This makes it easy for contributors to work independently on different components without merge conflicts.

## New Directory Structure

```
src/housing/
├── __init__.py                          # Main package exports
├── components/
│   ├── __init__.py                     # Components package exports
│   ├── constants.py                     # Shared constants
│   ├── utils.py                         # Utility functions
│   │
│   ├── loaders/                         # DATA LOADERS
│   │   ├── __init__.py
│   │   ├── rental_data.py               # RentalDataLoader
│   │   ├── zip_boundaries.py            # ZipBoundariesLoader
│   │   ├── community_boundaries.py      # CommunityBoundariesLoader
│   │   └── tract_boundaries.py          # TractBoundariesLoader
│   │
│   ├── processors/                      # DATA PROCESSORS
│   │   ├── __init__.py
│   │   ├── zip_to_tract.py              # ZipToTractProcessor
│   │   └── tract_to_community.py        # TractToCommunityProcessor
│   │
│   ├── analyzers/                       # ANALYZERS
│   │   ├── __init__.py
│   │   ├── correlation.py               # CorrelationAnalyzer
│   │   └── tract.py                     # TractAnalyzer
│   │
│   └── visualizers/                     # VISUALIZERS
│       ├── __init__.py
│       └── correlation.py               # CorrelationVisualizer
│
└── scripts/
    ├── __init__.py
    └── housing_eda_pipeline.py          # Main housing pipeline
```

## Component Organization

### `components/loaders/`
Each data loader gets its own file:
- **`rental_data.py`** - Loads ZORI rental price data
- **`zip_boundaries.py`** - Loads zip code boundaries
- **`community_boundaries.py`** - Loads community area boundaries
- **`tract_boundaries.py`** - Loads census tract boundaries

### `components/processors/`
Spatial processing components:
- **`zip_to_tract.py`** - Transforms data from zip to tract level
- **`tract_to_community.py`** - Aggregates tract data to community level

### `components/analyzers/`
Statistical analysis components:
- **`correlation.py`** - Community-level correlation analysis
- **`tract.py`** - Tract-level analysis

### `components/visualizers/`
Visualization components:
- **`correlation.py`** - Creates correlation visualizations

### `components/constants.py`
Shared constants used across components:
- Correlation thresholds
- Analysis parameters

### `components/utils.py`
Utility functions:
- `summary_reporter` - Generates summary reports

## Import Patterns

```python
# In a loader file (e.g., loaders/rental_data.py)
from pipeline.base import DataLoader
import pandas as pd
import logging

class RentalDataLoader(DataLoader):
    ...
```

```python
# In an analyzer file (e.g., analyzers/correlation.py)
from pipeline.base import Analyzer
from housing.components.constants import CORRELATION_STRONG_THRESHOLD

class CorrelationAnalyzer(Analyzer):
    ...
```