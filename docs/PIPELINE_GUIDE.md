# Pipeline Guide

This guide covers the core pipeline architecture and available components for housing analysis.

## Why Pipelines?

Pipelines break complex analysis into reusable, testable components:

```python
# Clean, maintainable approach
from pipeline import Pipeline
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.analyzers.rental_correlation import RentalCorrelationAnalyzer

pipeline = Pipeline("Housing Analysis")
pipeline.register_component(RentalDataLoader())
pipeline.register_component(ZipToTractProcessor())
pipeline.register_component(RentalCorrelationAnalyzer())
results = pipeline.execute()
```

**Benefits:**
- Each component is independently testable
- Easy to reuse components across projects
- Clear error messages and logging
- Components can be developed in parallel

## Core Architecture

### Context (Shared Memory)
Components share data through a context dictionary:

```python
context = {}  # Start empty

# Component 1: Loader adds data
result = loader.execute(context)  # Returns: {"rental_data": DataFrame}
context.update(result)

# Component 2: Processor uses data from context
rental = context["rental_data"]  # Access previous results
result = processor.execute(context)  # Returns: {"processed_data": DataFrame}
context.update(result)
```

### Component Types

| Type | Purpose | Example |
|------|---------|---------|
| **DataLoader** | Load data from files/APIs | `RentalDataLoader`, `AirbnbDataLoader` |
| **DataProcessor** | Transform/aggregate data | `ZipToTractProcessor`, `PointsToTractProcessor` |
| **Analyzer** | Statistical analysis | `STRProhibitionAnalyzer` |
| **Visualizer** | Create plots/maps | `RentalMapVisualizer`, `AirbnbDistributionVisualizer` |

## Available Components

### Data Loaders
- `RentalDataLoader` - ZORI rental price data
- `AirbnbDataLoader` - Airbnb listings data
- `STRProhibitionDataLoader` - STR prohibition data
- `TractBoundariesLoader` - Census tract boundaries
- `CommunityBoundariesLoader` - Community area boundaries
- `ZipBoundariesLoader` - ZIP code boundaries
- `CityBoundariesLoader` - Chicago city boundaries

### Data Processors
- `ZipToTractProcessor` - ZIP → Tract spatial join
- `PointsToTractProcessor` - Point data → Tract aggregation
- `TractToCommunityProcessor` - Tract → Community aggregation

### Analyzers
- `RentalCorrelationAnalyzer` - Community-level rental correlations
- `RentalTractAnalyzer` - Tract-level rental analysis
- `STRProhibitionAnalyzer` - STR units density and correlations (units per km²)

### Visualizers
- `RentalMapVisualizer` - Rental price spatial maps
- `RentalDistributionVisualizer` - Rental price distributions
- `AirbnbMapVisualizer` - Airbnb spatial maps
- `AirbnbDistributionVisualizer` - Airbnb distributions
- `STRMapVisualizer` - STR prohibition maps
- `STRDistributionVisualizer` - STR prohibition distributions
- `STRProhibitionVisualizer` - STR correlation analysis

## Creating Components

### Component Template

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
        
        # Get data from context (if needed)
        # input_data = context.get("some_data")
        
        # Your logic here
        result = {"my_data": processed_data}
        
        return result
```

### Import Pattern

Use direct imports:

```python
# Direct imports (recommended)
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.analyzers.str_prohibition import STRProhibitionAnalyzer

# Or from main package
from housing import RentalDataLoader, STRProhibitionAnalyzer
```

## Common Patterns

### Spatial Analysis Pipeline
```python
pipeline = Pipeline("Spatial Analysis")

# Load data
pipeline.register_component(RentalDataLoader())
pipeline.register_component(TractBoundariesLoader())

# Process
pipeline.register_component(ZipToTractProcessor())
pipeline.register_component(TractToCommunityProcessor())

# Analyze
pipeline.register_component(RentalCorrelationAnalyzer())

# Visualize
pipeline.register_component(RentalMapVisualizer())

results = pipeline.execute()
```

### Point Data Analysis
```python
# For Airbnb or STR prohibition data
pipeline.register_component(AirbnbDataLoader())
pipeline.register_component(TractBoundariesLoader())
pipeline.register_component(PointsToTractProcessor("airbnb_data", "airbnb_tract_data"))
pipeline.register_component(TractToCommunityProcessor())
```

## Configuration

Components use default file paths that can be overridden when instantiating loaders:

```python
# Use default paths
pipeline.register_component(RentalDataLoader())

# Override specific paths
pipeline.register_component(RentalDataLoader(
    file_path="/custom/path/to/rental_data.csv"
))
```

Default paths are defined in each loader's `__init__` method:
- Rental data: `/project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv`
- Tract boundaries: `/project/data/tl_2023_17_tract/tl_2023_17_tract.shp`
- Airbnb data: `/project/data/listings.csv`
- API endpoints for Chicago Data Portal (URLs, cached automatically)

To customize paths across multiple loaders, pass file paths when instantiating each loader.

## Error Handling

Components handle errors gracefully:

```python
# Safe context access
if "required_data" not in context:
    logger.error("Required data missing from context")
    return {}
data = context["required_data"]
```

## Best Practices

- **Use direct imports** for clarity
- **Check context keys** before accessing data
- **Log important steps** with `logger.info()`
- **Return clear dictionary keys** from components
- **Handle missing data** gracefully
- **Override file paths** when instantiating loaders if defaults don't match your setup