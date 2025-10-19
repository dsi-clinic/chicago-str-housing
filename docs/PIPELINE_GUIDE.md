# Spatial Data Analysis Pipeline - Quick Start Guide

---

## Why Pipelines?

### The Problem

**Real-world scenario:** You're analyzing Chicago housing data and need to:
1. Load rental data from CSV
2. Load multiple boundary files (ZIP, tract, community)
3. Perform spatial joins and aggregations
4. Run statistical analysis
5. Create visualizations
6. Generate reports

**The naive approach (what NOT to do):**
```python
# One giant script - a nightmare to maintain!
import pandas as pd
import geopandas as gpd

# Load everything
rental_data = pd.read_csv("rentals.csv")
zip_boundaries = gpd.read_file("zips.geojson")
# ... 200 lines of spaghetti code ...
# What if one step fails? Start over!
# What if you want to reuse the spatial join? Copy-paste!
```

**Problems:**
- Can't reuse individual steps
- Hard to test and debug
- If step 5 fails, you re-run steps 1-4 unnecessarily
- Team members can't work independently
- No clear logging of what happened

### The Pipeline Solution

```python
# The pipeline way - clean, maintainable, powerful
from pipeline import Pipeline
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.processors.tract_to_community import TractToCommunityProcessor
from housing.components.analyzers.rental_correlation import RentalCorrelationAnalyzer
from housing.components.visualizers.rental_correlation import RentalCorrelationVisualizer

pipeline = Pipeline("Housing Analysis")
pipeline.register_component(RentalDataLoader())
pipeline.register_component(ZipToTractProcessor())
pipeline.register_component(TractToCommunityProcessor())
pipeline.register_component(RentalCorrelationAnalyzer())
pipeline.register_component(RentalCorrelationVisualizer())

results = pipeline.execute()
```

**Benefits:**
- Each component is independently testable
- Easy to reuse components
- Clear error messages
- Components can be developed in parallel
- Automatic logging of execution flow
- Results cached in shared context

---

## Core Architecture

### The Context (Shared Memory)

Think of `context` as a **shared whiteboard** that all components can read from and write to.

```python
context = {}  # Start empty

# Component 1: RentalDataLoader
result = rental_loader.execute(context)
# Returns: {"rental_data": DataFrame}
context.update(result)
# Context now: {"rental_data": DataFrame}

# Component 2: ZipBoundariesLoader  
result = zip_loader.execute(context)
# Returns: {"zip_boundaries": GeoDataFrame}
context.update(result)
# Context now: {"rental_data": DataFrame, "zip_boundaries": GeoDataFrame}

# Component 3: SpatialJoinProcessor
# Reads from context!
rental = context["rental_data"]  # ← Access previous results
zips = context["zip_boundaries"]  # ← Access previous results
# ... do spatial join ...
# Returns: {"tract_rental_data": GeoDataFrame}
context.update(result)
```

### The Three Core Abstractions

**1. PipelineComponent (The Worker)**
```python
class PipelineComponent(ABC):
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.dependencies = []
    
    @abstractmethod
    def execute(self, context):
        # Read from context: data = context["previous_result"]
        # Do your work
        # Return results: return {"new_result": processed_data}
        pass
```

**2. Pipeline (The Conductor)**
```python
class Pipeline:
    def __init__(self, name):
        self.name = name
        self.components = {}    # Registry
        self.context = {}       # Shared data
        self.results = []       # Execution history
    
    def register_component(self, component):
        self.components[component.name] = component
    
    def execute(self):
        for name, component in self.components.items():
            result = component.execute(self.context)
            self.context.update(result.data)
            self.results.append(result)
        return self.results
```

**3. PipelineResult (The Receipt)**
```python
@dataclass
class PipelineResult:
    component_name: str
    success: bool
    execution_time: float
    data: dict
    error: str | None
```

---

## Three Ways to Create Components

### Decision Guide

```
Does it load data from a file?        → Use DataLoader
Does it transform/merge data?         → Use DataProcessor  
Does it do statistical analysis?      → Use Analyzer
Does it create visualizations?        → Use Visualizer
Is it a simple, one-off function?     → Use @pipeline_component decorator
Need full control?                    → Use PipelineComponent base class
```

### Method 1: Inherit from Base Classes (Recommended)

```python
from pipeline.base import DataLoader

class RentalDataLoader(DataLoader):
    """Load rental price data from CSV."""
    
    def __init__(self):
        super().__init__("rental_data", "Loads rental prices by ZIP")
    
    def execute(self, context):
        data = pd.read_csv(self.config.data.rental_data_path)
        return {"rental_data": data}
```

**Four base classes:**
- `DataLoader` - Load data from files
- `DataProcessor` - Transform/merge data
- `Analyzer` - Statistical analysis
- `Visualizer` - Create plots

### Method 2: Inherit from PipelineComponent (Flexible)

```python
from pipeline.base import PipelineComponent

class CustomAnalyzer(PipelineComponent):
    def __init__(self):
        super().__init__("custom", "My custom analysis")
        self.dependencies = ["rental_data"]  # Declare dependencies
    
    def execute(self, context):
        data = context["rental_data"]
        result = data.describe()
        return {"analysis_results": result}
```

### Method 3: Use @pipeline_component Decorator (Quick)

```python
from pipeline.base import pipeline_component

@pipeline_component(
    name="quick_analyzer",
    description="Quick analysis function"
)
def analyze_data(context):
    data = context["rental_data"]
    return {"mean_rent": data["price"].mean()}
```

**Comparison:**

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| Base Classes | Standard tasks | Clear, self-documenting | Medium boilerplate |
| PipelineComponent | Custom tasks | Maximum flexibility | More code |
| Decorator | Prototypes | Fastest to write | Harder to test |

---

## Chicago Housing Pipeline Example

### The Challenge

Rental prices are by ZIP code, but we want analysis by community area. ZIP codes and community areas don't align perfectly, so we need **two-step spatial aggregation** through census tracts.

### Why a Pipeline?

1. **Multiple data sources**: rentals (CSV), ZIP boundaries, tract boundaries, community boundaries
2. **Complex operations**: ZIP → Tract → Community with area-weighted aggregation
3. **Data quality**: Spatial interpolation (K-nearest neighbors) fills missing values
4. **Reusability**: Spatial join logic used in multiple projects

### The Flow

```python
# 1. Data Loading
RentalDataLoader()          # Load rental prices by ZIP
  → Returns: {"rental_data": DataFrame}

ZipBoundariesLoader()       # Load ZIP geometries  
  → Returns: {"zip_boundaries": GeoDataFrame}

TractBoundariesLoader()     # Load tract geometries
  → Returns: {"tract_boundaries": GeoDataFrame}

CommunityBoundariesLoader() # Load community geometries
  → Returns: {"community_boundaries": GeoDataFrame}

# 2. Two-Step Spatial Aggregation
ZipToTractProcessor()       # First aggregation
  → Reads: rental_data, zip_boundaries, tract_boundaries
  → Does: Spatial join + area-weighted aggregation + KNN interpolation
  → Returns: {"tract_rental_data": GeoDataFrame}

TractToCommunityProcessor() # Second aggregation
  → Reads: tract_rental_data, community_boundaries
  → Does: Spatial join + area-weighted aggregation
  → Returns: {"community_rental_data": GeoDataFrame}

# 3. Analysis
RentalCorrelationAnalyzer()
  → Reads: community_rental_data
  → Returns: {"correlation_results": dict}

# 4. Visualization
RentalCorrelationVisualizer()
  → Reads: correlation_results
  → Returns: {"correlation_plot": Figure}
```

### Why Two-Step Aggregation?

- **Granularity**: Census tracts (801) provide finer resolution
- **Accuracy**: Area-weighted aggregation at each step preserves spatial precision
- **Flexibility**: Can analyze at tract level OR community level
- **Data quality**: Spatial interpolation fills gaps

---

## Quick Start: Build Your First Component

### Step 1: Create the Component

```python
# In src/housing/components/analyzers/my_analyzer.py
from pipeline.base import Analyzer
import logging

logger = logging.getLogger(__name__)

class QuickStatsAnalyzer(Analyzer):
    """Calculate rental price statistics."""
    
    def __init__(self):
        super().__init__(
            "quick_stats",
            "Calculate mean, median, std of rental prices"
        )
    
    def execute(self, context):
        data = context["community_rental_data"]
        
        stats = {
            "mean_rent": data["avg_rental_price"].mean(),
            "median_rent": data["avg_rental_price"].median(),
            "std_rent": data["avg_rental_price"].std(),
        }
        
        logger.info(f"Calculated stats: {stats}")
        return {"quick_stats": stats}
```

### Step 2: Use It in a Pipeline

```python
from pipeline import Pipeline
from pipeline.config import PipelineConfig
from housing.components.analyzers.my_analyzer import QuickStatsAnalyzer

# Create pipeline
config = PipelineConfig()
pipeline = Pipeline("My Analysis", config=config)
pipeline.load_config()

# Register components
pipeline.register_component(QuickStatsAnalyzer())

# Run it
results = pipeline.execute()

# Access results
stats = pipeline.context["quick_stats"]
print(f"Average rent: ${stats['mean_rent']:.2f}")
```

---

## Configuration

### Using pipeline_config.yaml

```yaml
data:
  rental_data_path: data/rentals.csv
  zip_boundaries_path: data/zip_boundaries.csv
  tract_boundaries_path: data/tract_boundaries.csv
  community_boundaries_path: data/community_boundaries.csv

output:
  output_dir: output/
  save_intermediates: true

analysis:
  correlation_threshold: 0.5
```

### Accessing Config in Components

```python
class MyLoader(DataLoader):
    def execute(self, context):
        # Access config values
        path = self.config.data.rental_data_path
        data = pd.read_csv(path)
        return {"data": data}
```

---

## Testing Your Components

### Test Individual Components

```python
# tests/test_my_analyzer.py
from housing.components.analyzers.my_analyzer import QuickStatsAnalyzer
import pandas as pd

def test_quick_stats():
    # Arrange
    analyzer = QuickStatsAnalyzer()
    mock_data = pd.DataFrame({
        "avg_rental_price": [1000, 1500, 2000]
    })
    context = {"community_rental_data": mock_data}
    
    # Act
    result = analyzer.execute(context)
    
    # Assert
    assert "quick_stats" in result
    assert result["quick_stats"]["mean_rent"] == 1500
```

### Test Full Pipeline

```python
def test_full_pipeline():
    pipeline = Pipeline("test")
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(QuickStatsAnalyzer())
    
    results = pipeline.execute()
    assert all(r.success for r in results)
```

---

## Repository Structure

```
src/
├── pipeline/
│   ├── base.py          # Core architecture
│   ├── config.py        # Configuration management
│   └── scripts/         # Usage examples
│
├── housing/
│   ├── components/
│   │   ├── loaders/     # Data loaders
│   │   ├── processors/  # Data processors
│   │   ├── analyzers/   # Analysis components
│   │   └── visualizers/ # Visualization components
│   └── scripts/         # Pipeline scripts

tests/
└── test_pipeline_system.py

notebooks/
└── tract_analysis_demo.ipynb  # Interactive demo
```

---

## Key Takeaways

### The Three-Step Recipe
1. **Choose your approach**: Base class, PipelineComponent, or decorator
2. **Write execute() method**: Takes `context`, returns `dict`
3. **Register and run**: Add to pipeline, call `execute()`

### Important Rules
- Always return a dict from `execute()`
- Dict keys become available in `context`
- Components execute in registration order
- Later components can access earlier results via `context`

### Where to Learn More
- **Example Code:**
  - `notebooks/tract_analysis_demo.ipynb` - Interactive demo
  - `src/pipeline/scripts/pipeline_usage.py` - Usage examples
  - `tests/test_pipeline_system.py` - Testing examples

---

## Frequently Asked Questions

**How do I know what's in context?**  
Print `pipeline.context.keys()` or look at what previous components returned.

**Can components fail gracefully?**  
Yes! Wrap your code in try/except. The pipeline catches errors and continues.

**How do I access configuration?**  
Use `self.config` in components.

**What about dependencies between components?**  
Set `self.dependencies = ['component_name']` - the pipeline handles ordering.