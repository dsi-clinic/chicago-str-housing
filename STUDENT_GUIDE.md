# Student Guide: Working with Housing Components

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
- `ZipBoundariesLoader` - Zip code boundaries
- `CommunityBoundariesLoader` - Community area boundaries  
- `TractBoundariesLoader` - Census tract boundaries

#### Processors
- `ZipToTractProcessor` - Zip → Tract spatial join
- `TractToCommunityProcessor` - Tract → Community aggregation

#### Analyzers
- `CorrelationAnalyzer` - Community-level correlation analysis
- `TractAnalyzer` - Tract-level analysis

#### Visualizers
- `CorrelationVisualizer` - Creates correlation plots

## How to Create a New Component

### Step 1: Choose Component Type

Decide what type of component you're creating:
- **Loader**: Loads data from files
- **Processor**: Transforms or joins data
- **Analyzer**: Performs statistical analysis
- **Visualizer**: Creates charts/visualizations

### Step 2: Create Your File

Create a new `.py` file in the appropriate directory:

```bash
# For a new loader
touch src/housing/components/loaders/my_loader.py

# For a new analyzer
touch src/housing/components/analyzers/my_analyzer.py
```

### Step 3: Write Your Component

Use this template based on your component type:

#### **Template: Data Loader**

```python
"""Description of what data this loads."""

import logging
from typing import Any
import pandas as pd

from pipeline.base import DataLoader

logger = logging.getLogger(__name__)


class MyDataLoader(DataLoader):
    """Load my custom data.
    
    Detailed description of what this component does.
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the loader.
        
        Args:
            file_path: Optional path to data file
        """
        super().__init__(
            "my_data",  # Name used in pipeline context
            file_path or "/project/data/my_data.csv",
            "Load my custom data",  # Description
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Load and process the data."""
        logger.info("Loading data from: %s", self.file_path)
        
        # Your loading logic here
        df = pd.read_csv(self.file_path)
        
        # Clean and process data
        # ...
        
        logger.info("Loaded %d records", len(df))
        
        # Return data with a key name
        return {"my_data": df}
```

#### **Template: Processor**

```python
"""Description of what processing this does."""

import logging
from typing import Any
import geopandas as gpd

from pipeline.base import DataProcessor

logger = logging.getLogger(__name__)


class MyProcessor(DataProcessor):
    """Process data in some way.
    
    Detailed description.
    """

    def __init__(self) -> None:
        """Initialize the processor."""
        super().__init__(
            "my_processor",
            "Process and transform data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform the processing."""
        logger.info("Processing data...")
        
        # Get data from context
        input_data = context["some_input_data"]
        
        # Your processing logic here
        processed_data = input_data  # ... transform it
        
        logger.info("Processing complete")
        
        return {"processed_data": processed_data}
```

#### **Template: Analyzer**

```python
"""Description of what analysis this performs."""

import logging
from typing import Any

from pipeline.base import Analyzer
from housing.components.constants import CORRELATION_STRONG_THRESHOLD

logger = logging.getLogger(__name__)


class MyAnalyzer(Analyzer):
    """Analyze data to find insights.
    
    Detailed description.
    """

    def __init__(self) -> None:
        """Initialize the analyzer."""
        super().__init__(
            "my_analysis",
            "Perform statistical analysis on data",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Perform the analysis."""
        logger.info("Performing analysis...")
        
        # Get data from context
        data = context["input_data"]
        
        # Your analysis logic here
        results = {}  # Calculate statistics, correlations, etc.
        
        logger.info("Analysis complete")
        
        return {"analysis_results": results}
```

### Step 4: Register Your Component

Add your component to the appropriate `__init__.py`:

```python
# In src/housing/components/loaders/__init__.py
from housing.components.loaders.my_loader import MyDataLoader

__all__ = [
    ...,
    "MyDataLoader",  # Add your component
]
```

```python
# In src/housing/components/__init__.py  
from housing.components.loaders import MyDataLoader

__all__ = [
    ...,
    "MyDataLoader",  # Add your component
]
```

### Step 5: Use Your Component

Now you can use it in pipelines:

```python
from housing import MyDataLoader
from pipeline import Pipeline

pipeline = Pipeline("My Analysis")
pipeline.register_component(MyDataLoader())
results = pipeline.execute()
```

## Testing Your Component

### Unit Test Template

```python
# In tests/test_my_component.py
import pytest
from housing import MyDataLoader

def test_my_loader_success():
    """Test MyDataLoader with valid data."""
    # Arrange
    loader = MyDataLoader()
    
    # Act
    result = loader.execute({})
    
    # Assert
    assert isinstance(result, dict)
    assert "my_data" in result
    assert len(result["my_data"]) > 0
```

### Run Tests

```bash
# Run all tests
make test

# Run specific test file
uv run python -m pytest tests/test_my_component.py -v
```

## Common Patterns

### Using Constants

```python
from housing.components.constants import (
    CORRELATION_STRONG_THRESHOLD,
    CORRELATION_MODERATE_THRESHOLD,
)

if correlation >= CORRELATION_STRONG_THRESHOLD:
    strength = "Strong"
```

### Accessing Context Data

```python
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    # Data added by previous components
    rental_data = context["rental_data"]
    boundaries = context["zip_boundaries"]
    
    # Use the data
    # ...
    
    # Return new data to context
    return {"my_result": result}
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing %d records", len(data))
logger.warning("Missing data for zip code: %s", zip_code)
logger.error("Failed to process: %s", error_msg)
```

## Tips & Best Practices

### DO:
- Use descriptive component names
- Add docstrings to classes and methods
- Log important steps and results
- Handle errors gracefully
- Return results in a dictionary with clear keys
- Write tests for your components

### DON'T:
- Hardcode file paths (use parameters)
- Assume data exists (check first)
- Ignore errors (log and handle them)
- Create circular dependencies between components
- Modify data in the context directly

## Getting Help

### Example Components to Study

Start by looking at these well-documented examples:

1. **Simple Loader**: `loaders/rental_data.py`
2. **Spatial Processor**: `processors/zip_to_tract.py`
3. **Statistical Analyzer**: `analyzers/correlation.py`
4. **Visualizer**: `visualizers/correlation.py`

### Common Issues

**Import Error:**
```python
# Wrong
from components.loaders import MyLoader

# Correct
from housing.components.loaders import MyLoader
# or
from housing import MyLoader
```

**Context Key Error:**
```python
# Risky - will crash if key missing
data = context["my_data"]

# Safe - checks first
if "my_data" not in context:
    logger.error("Required data 'my_data' not in context")
    return {}
data = context["my_data"]
```

**File Path Error:**
```python
# Hardcoded
def __init__(self):
    self.path = "/home/student/data.csv"

# Configurable with default
def __init__(self, file_path: str | None = None):
    self.path = file_path or "/project/data/default.csv"
```

## Resources

- **Pipeline Guide**: `PIPELINE_GUIDE.md`
- **Component Structure**: `COMPONENT_STRUCTURE.md`
- **Tests**: `tests/test_pipeline_system.py`

## Quick Commands

```bash
# Run housing pipeline
make test-pipeline

# Run generic pipeline demo
make test-generic-pipeline

# Run all tests
make test

# Interactive shell
make run-interactive

# Build container
make build-only
```

Good luck with your components!

