# Student Guide

Quick guide for working with housing analysis components.

## Quick Start

### Run the Main Pipeline

```bash
# Run the complete housing analysis
docker compose run --rm 2025-autumn-city-of-chicago-housing python src/housing/scripts/housing_eda_pipeline.py
```

This generates:
- Rental price distributions and maps
- STR prohibition analysis and correlations  
- Airbnb listings analysis
- All visualizations saved to `output/`

## Available Components

### Data Loaders
- `RentalDataLoader` - ZORI rental price data
- `AirbnbDataLoader` - Airbnb listings data
- `STRProhibitionDataLoader` - STR prohibition data
- `TractBoundariesLoader`, `CommunityBoundariesLoader`, `ZipBoundariesLoader`, `CityBoundariesLoader`

### Processors
- `ZipToTractProcessor` - ZIP → Tract spatial join
- `PointsToTractProcessor` - Point data → Tract aggregation
- `TractToCommunityProcessor` - Tract → Community aggregation

### Analyzers
- `RentalTractAnalyzer` - Tract-level analysis
- `STRProhibitionAnalyzer` - STR units density analysis (units per km²)

### Visualizers
- `RentalMapVisualizer`, `RentalDistributionVisualizer` - Rental analysis
- `AirbnbMapVisualizer`, `AirbnbDistributionVisualizer` - Airbnb analysis
- `STRMapVisualizer`, `STRDistributionVisualizer` - STR analysis
- `STRProhibitionVisualizer` - STR correlation charts

## Creating New Components

### 1. Copy Similar Component
```bash
# Example: Create new loader
cp src/housing/components/loaders/rental_data.py src/housing/components/loaders/my_loader.py
```

### 2. Template
```python
from pipeline.base import DataLoader
from typing import Any
import logging

logger = logging.getLogger(__name__)

class MyComponent(DataLoader):
    def __init__(self, file_path: str | None = None) -> None:
        super().__init__(
            "my_component",  # Name (key in context)
            file_path or "/project/data/default.csv",
            "Brief description",
        )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("Starting my component...")
        
        # Your logic here
        result = {"my_data": processed_data}
        return result
```

### 3. Use Direct Imports
```python
# In your pipeline script
from housing.components.loaders.my_loader import MyComponent

pipeline.register_component(MyComponent())
```

## Common Patterns

### Spatial Analysis
```python
pipeline = Pipeline("Spatial Analysis")
pipeline.register_component(RentalDataLoader())
pipeline.register_component(TractBoundariesLoader())
pipeline.register_component(ZipToTractProcessor())
pipeline.register_component(TractToCommunityProcessor())
pipeline.register_component(RentalTractAnalyzer())
results = pipeline.execute()
```

### Point Data Analysis
```python
# For Airbnb or STR data
pipeline.register_component(AirbnbDataLoader())
pipeline.register_component(TractBoundariesLoader())
pipeline.register_component(PointsToTractProcessor("airbnb_data", "airbnb_tract_data"))
pipeline.register_component(TractToCommunityProcessor())
```

## Adding New Data Sources

### 1. Create Data Loader
```python
class MyDataLoader(DataLoader):
    def __init__(self) -> None:
        super().__init__("my_data", "Load my data")

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # Load your data
        df = pd.read_csv("/path/to/data.csv")
        return {"my_data": df}
```

### 2. Add to Pipeline
```python
from housing.components.loaders.my_data import MyDataLoader
pipeline.register_component(MyDataLoader())
```

### 3. Process if Needed
```python
# If it's point data, aggregate to tracts
if is_point_data:
    pipeline.register_component(PointsToTractProcessor("my_data", "my_tract_data"))
```

## Testing

### Run Tests
```bash
# All tests
make test

# Specific test
uv run python -m pytest tests/test_my_component.py -v
```

### Write Tests
```python
def test_my_component():
    component = MyComponent()
    context = {}  # Add required context data
    result = component.execute(context)
    assert "my_data" in result
```

## Troubleshooting

### Import Errors
```python
# ❌ Wrong
from components.loaders import MyLoader

# ✅ Correct - direct import
from housing.components.loaders.my_loader import MyLoader
```

### Missing Context Data
```python
# ❌ Risky
data = context["my_data"]

# ✅ Safe
if "my_data" not in context:
    logger.error("Required data missing")
    return {}
data = context["my_data"]
```

### File Paths
```python
# ❌ Hardcoded
def __init__(self):
    self.path = "/home/student/data.csv"

# ✅ Configurable
def __init__(self, file_path: str | None = None):
    self.path = file_path or "/project/data/default.csv"
```

## Best Practices

- **Use direct imports** for clarity
- **Check context keys** before accessing data
- **Log important steps** with `logger.info()`
- **Handle errors gracefully** with try/except
- **Use configuration** for file paths
- **Return clear dictionary keys**
- **Write tests** for new components