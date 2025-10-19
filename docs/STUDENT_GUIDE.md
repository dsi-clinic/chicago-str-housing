# Student Guide: Working with Housing Components

**Prerequisites:** Read [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md) for core pipeline concepts.

---

## Quick Reference

### Component File Locations

| Component Type | Location | Example |
|---------------|----------|---------|
| **Data Loaders** | `src/housing/components/loaders/` | `rental_data.py` |
| **Processors** | `src/housing/components/processors/` | `zip_to_tract.py` |
| **Analyzers** | `src/housing/components/analyzers/` | `correlation.py` |
| **Visualizers** | `src/housing/components/visualizers/` | `correlation.py` |
| **Constants** | `src/housing/components/constants.py` | Thresholds, config |
| **Utilities** | `src/housing/components/utils.py` | Helper functions |

### Available Components

#### Data Loaders
- `RentalDataLoader` - ZORI rental price data
- `ZipBoundariesLoader` - ZIP code boundaries
- `CommunityBoundariesLoader` - Community area boundaries  
- `TractBoundariesLoader` - Census tract boundaries
- `AirbnbDataLoader` - Airbnb listing data
- `STRProhibitionDataLoader` - STR prohibition data

#### Processors
- `ZipToTractProcessor` - ZIP → Tract spatial join (includes KNN interpolation)
- `TractToCommunityProcessor` - Tract → Community aggregation
- `AirbnbToTractProcessor` - Airbnb → Tract aggregation

#### Analyzers
- `RentalCorrelationAnalyzer` - Community-level rental correlation analysis
- `RentalTractAnalyzer` - Tract-level rental analysis
- `AirbnbRentalAnalyzer` - Airbnb vs rental price analysis
- `STRProhibitionAnalyzer` - STR prohibition density analysis
- `STRTemporalAnalyzer` - Temporal pattern analysis

#### Visualizers
- `RentalCorrelationVisualizer` - Rental correlation plots
- `AirbnbMapVisualizer` - Airbnb spatial maps
- `STRProhibitionVisualizer` - STR prohibition charts
- `STRDensityMapVisualizer` - STR density maps
- `STRTemporalVisualizer` - Temporal analysis plots

---

## How to Create a New Component

### Step 1: Choose Your Starting Point

**Copy an existing component similar to what you need:**
- New loader? Copy `loaders/rental_data.py`
- New spatial processor? Copy `processors/zip_to_tract.py`
- New analyzer? Copy `analyzers/correlation.py`
- New visualizer? Copy `visualizers/correlation.py`

### Step 2: Component Template

```python
"""Brief description of what this component does."""

import logging
from typing import Any
import pandas as pd

from pipeline.base import DataLoader  # or DataProcessor, Analyzer, Visualizer

logger = logging.getLogger(__name__)


class MyComponent(DataLoader):
    """One-line summary.
    
    Detailed explanation of what this does, inputs, and outputs.
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the component.
        
        Args:
            file_path: Path to data file (optional)
        """
        super().__init__(
            "my_component",  # Name (key in context)
            file_path or "/project/data/default.csv",
            "Brief description",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the component logic.
        
        Args:
            context: Pipeline context with data from previous components
            
        Returns:
            Dictionary with results to add to context
        """
        logger.info("Starting my component...")
        
        # Get data from context (if needed)
        # input_data = context.get("some_data")
        
        # Your logic here
        df = pd.read_csv(self.file_path)
        
        logger.info("Processed %d records", len(df))
        
        return {"my_data": df}
```

### Step 3: Register Your Component

```python
# 1. Add to the specific __init__.py
# In src/housing/components/loaders/__init__.py
from housing.components.loaders.my_component import MyComponent

__all__ = [
    # ... existing components
    "MyComponent",
]

# 2. Add to the main __init__.py
# In src/housing/components/__init__.py  
from housing.components.loaders import MyComponent

__all__ = [
    # ... existing components
    "MyComponent",
]
```

### Step 4: Use in a Pipeline

```python
from pipeline import Pipeline
from pipeline.config import PipelineConfig
from housing.components import MyComponent

config = PipelineConfig()
pipeline = Pipeline("My Analysis", config=config)
pipeline.load_config()

pipeline.register_component(MyComponent())
results = pipeline.execute()

# Access your results
my_data = pipeline.context["my_data"]
```

---

## Common Issues & Solutions

### Import Errors

```python
# ❌ Wrong
from components.loaders import MyLoader

# ✅ Correct
from housing.components.loaders import MyLoader
# or
from housing import MyLoader
```

### Missing Context Keys

```python
# ❌ Risky - crashes if key missing
data = context["my_data"]

# ✅ Safe - checks first
if "my_data" not in context:
    logger.error("Required data 'my_data' not in context")
    return {}
data = context["my_data"]
```

### File Paths

```python
# ❌ Hardcoded
def __init__(self):
    self.path = "/home/student/data.csv"

# ✅ Configurable with default
def __init__(self, file_path: str | None = None):
    self.path = file_path or "/project/data/default.csv"
    
# ✅✅ Even better - use config
def execute(self, context):
    path = self.config.data.rental_data_path
```

---

## Testing

### Write a Simple Test

```python
# In tests/test_my_component.py
import pytest
from housing.components import MyComponent

def test_my_component():
    # Arrange
    component = MyComponent()
    context = {}  # Add any required context data
    
    # Act
    result = component.execute(context)
    
    # Assert
    assert "my_data" in result
    assert len(result["my_data"]) > 0
```

### Run Tests

```bash
# All tests
make test

# Specific test
uv run python -m pytest tests/test_my_component.py -v
```

---

## Project-Specific Tips

### Using Constants

```python
from housing.components.constants import (
    CORRELATION_STRONG_THRESHOLD,
    CORRELATION_MODERATE_THRESHOLD,
)

if correlation >= CORRELATION_STRONG_THRESHOLD:
    strength = "Strong"
```

### Logging Best Practices

```python
import logging
logger = logging.getLogger(__name__)

# Use meaningful messages
logger.info("Loading data from: %s", self.file_path)
logger.info("Loaded %d ZIP codes with rental data", len(df))
logger.warning("Missing rental price for %d ZIP codes", missing_count)
logger.error("Failed to load data: %s", str(e))
```

### Return Dictionary Structure

```python
# Always return a dict with clear, descriptive keys
return {
    "rental_data": df,              # Main data
    "rental_summary": summary_dict, # Optional summary info
    "rental_metadata": metadata     # Optional metadata
}
```

---

## Best Practices Checklist

When creating a new component:

- [ ] Chose appropriate base class (DataLoader, DataProcessor, Analyzer, Visualizer)
- [ ] Added type hints to methods
- [ ] Wrote docstrings for class and methods
- [ ] Used `logger.info()` for important steps
- [ ] Handled errors gracefully (try/except)
- [ ] Used config for file paths (not hardcoded)
- [ ] Checked context keys before accessing
- [ ] Returned results in a clear dict
- [ ] Registered in both `__init__.py` files
- [ ] Wrote at least one unit test
- [ ] Ran `ruff check` and `ruff format`

