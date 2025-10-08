# Spatial Data Analysis Pipeline

## The Big Picture - Why Pipelines?

### The Problem We're Solving

**Real-world scenario:**
You're analyzing Chicago housing data. You need to:
1. Load rental data from CSV
2. Load ZIP code boundaries from another file
3. Load community area boundaries from yet another file
4. Join rental data to ZIP codes spatially
5. Aggregate from ZIP codes to community areas
6. Run correlation analysis
7. Create visualizations
8. Generate a summary report

**The naive approach (what NOT to do):**
```python
# One giant script - a nightmare to maintain!
import pandas as pd
import geopandas as gpd

# Load everything
rental_data = pd.read_csv("rentals.csv")
zip_boundaries = gpd.read_file("zips.geojson")
community_boundaries = gpd.read_file("communities.geojson")

# Do all processing in one go
rental_data = rental_data.merge(zip_boundaries, on='zip_code')
# ... 200 lines of spaghetti code ...
# What if one step fails? Start over!
# What if you want to reuse the spatial join? Copy-paste!
# What if two people work on this? Merge conflict hell!
```

**Problems with the monolithic approach:**
- ❌ Can't reuse individual steps
- ❌ Hard to test (all-or-nothing)
- ❌ Difficult to debug (where did it break?)
- ❌ Impossible to parallelize
- ❌ Team members can't work independently
- ❌ No visibility into what's happening
- ❌ If step 5 fails, you re-run steps 1-4 unnecessarily

### The Pipeline Solution

```
Raw Materials → Station 1 → Station 2 → Station 3 → Final Product
   (Data)      (Load)      (Process)    (Analyze)   (Visualize)
```

**Key insight**: Break the monolithic script into **independent, composable components**.

```python
# The pipeline way - clean, maintainable, powerful
from pipeline import Pipeline
from pipeline.components import (
    RentalDataLoader,        # Station 1
    ZipBoundariesLoader,     # Station 2
    SpatialJoinProcessor,    # Station 3
    CorrelationAnalyzer,     # Station 4
    Visualizer               # Station 5
)

pipeline = Pipeline("Housing Analysis")
pipeline.register_component(RentalDataLoader())
pipeline.register_component(ZipBoundariesLoader())
pipeline.register_component(SpatialJoinProcessor())
pipeline.register_component(CorrelationAnalyzer())
pipeline.register_component(Visualizer())

results = pipeline.execute()
```

**Benefits:**
- ✅ Each component is independently testable
- ✅ Easy to reuse components in different pipelines
- ✅ Clear error messages (which component failed)
- ✅ Team members own specific components
- ✅ Can skip/replace components easily
- ✅ Logging shows exactly what's happening
- ✅ Results cached in context (don't recompute)

---

### How the Pipeline Works: The Architecture

**Core Concept: The Context (Shared Memory)**

Think of `context` as a **shared whiteboard** that all components can read from and write to.

```python
# Pipeline execution flow:

context = {}  # Start with empty context

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
# Can read from context!
result = processor.execute(context)
rental = context["rental_data"]  # ← Read previous results
zips = context["zip_boundaries"]  # ← Read previous results
# ... do spatial join ...
# Returns: {"community_rental_data": GeoDataFrame}
context.update(result)
# Context now has 3 items!

# And so on...
```

**Visual Diagram:**
```
┌─────────────────────────────────────────────────────────┐
│                      PIPELINE                           │
│                                                         │
│  ┌──────────────┐         ┌─────────────────────┐     │
│  │  Component 1 │────────→│     CONTEXT         │     │
│  │ (Data Loader)│  writes │  {rental_data: DF}  │     │
│  └──────────────┘         └─────────────────────┘     │
│         │                           │                   │
│         ↓                           ↓                   │
│  ┌──────────────┐         ┌─────────────────────┐     │
│  │  Component 2 │────────→│     CONTEXT         │     │
│  │  (Processor) │  writes │  {rental_data: DF   │     │
│  └──────────────┘         │   zip_data: GDF}    │     │
│         ↑                  └─────────────────────┘     │
│         │                           │                   │
│         └───────reads───────────────┘                   │
│                                                         │
│  Each component:                                        │
│  1. Reads from context (gets previous results)         │
│  2. Does its work                                       │
│  3. Writes to context (shares results)                 │
│  4. Returns a PipelineResult (success/failure)         │
└─────────────────────────────────────────────────────────┘
```

---

### The Three Core Abstractions

**1. PipelineComponent (The Worker)**
```python
class PipelineComponent(ABC):
    def __init__(self, name, description):
        self.name = name              # Unique identifier
        self.description = description
        self.dependencies = []         # What it needs to run
    
    @abstractmethod
    def execute(self, context):
        # Do your work here
        # Read from context: data = context["previous_result"]
        # Return results: return {"new_result": processed_data}
        pass
```

**2. Pipeline (The Orchestra Conductor)**
```python
class Pipeline:
    def __init__(self, name):
        self.name = name
        self.components = {}    # Registry of all components
        self.context = {}       # Shared data store
        self.results = []       # Execution history
    
    def register_component(self, component):
        # Add component to the pipeline
        self.components[component.name] = component
    
    def execute(self):
        # Run each component in order
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
    component_name: str      # Which component ran
    success: bool           # Did it work?
    execution_time: float   # How long did it take?
    data: dict             # What did it produce?
    error: str | None      # What went wrong (if failed)
```

---

### Why This Design? The Software Engineering Principles

**1. Separation of Concerns**
- Each component does ONE thing well
- `RentalDataLoader` only loads data, doesn't analyze it
- `CorrelationAnalyzer` only analyzes, doesn't load data
- Easy to understand, test, and maintain

**2. Single Responsibility Principle**
- Want to change how data loads? Edit the loader.
- Want to add new analysis? Add a new analyzer.
- No ripple effects through the codebase

**3. Open/Closed Principle**
- Pipeline is **open for extension** (add new components)
- Pipeline is **closed for modification** (don't change core `Pipeline` class)
- Add features by adding components, not by editing existing code

**4. Dependency Injection**
- Components declare what they need: `self.dependencies = ["rental_data"]`
- Pipeline ensures dependencies are met
- Loose coupling between components

**5. Inversion of Control**
- Components don't control the flow
- Pipeline controls when and how components execute
- Components just do their job when called

---

### Real-World Analogies

**Factory Assembly Line:**
- Raw materials (data files) enter at one end
- Each station (component) does one specific task
- Partially finished products pass between stations (context)
- Final product exits at the end
- If one station breaks, you know exactly where to fix


**Data Science Workflow:**
```
Traditional Jupyter Notebook:
Cell 1: Load data (100 lines)
Cell 2: Clean data (200 lines)  
Cell 3: Feature engineering (150 lines)
Cell 4: Analysis (300 lines)
Cell 5: Visualization (100 lines)
→ One giant notebook, hard to maintain

Pipeline Approach:
Component 1: DataLoader (50 lines, tested)
Component 2: DataCleaner (50 lines, tested)
Component 3: FeatureEngineer (50 lines, tested)
Component 4: Analyzer (50 lines, tested)
Component 5: Visualizer (50 lines, tested)
→ Five small, focused, reusable, testable components
```

---

### Advanced Features: Why This Pipeline is Powerful

**1. Automatic Dependency Resolution**
```python
# Components declare dependencies
class SpatialJoin(DataProcessor):
    def __init__(self):
        super().__init__("spatial_join", "...")
        self.dependencies = ["rental_data", "zip_boundaries"]

# Pipeline automatically:
# - Checks if dependencies are met
# - Determines correct execution order
# - Validates the DAG (no circular dependencies)
```

**2. Configuration Management**
```python
# All file paths, parameters in one place
config = PipelineConfig()
config.data.rental_data_path = "/data/rentals.csv"
config.analysis.correlation_threshold = 0.5

pipeline = Pipeline("analysis", config=config)
# Components can access: self.config.data.rental_data_path
```

**3. Error Handling & Recovery**
```python
# If a component fails:
# - Error is logged with context
# - Execution continues (or stops, configurable)
# - Previous successful results are preserved
# - You can debug just that component

results = pipeline.execute()
for result in results:
    if not result.success:
        print(f"{result.component_name} failed: {result.error}")
        # Fix the component and re-run just that one
```

**4. Observability & Logging**
```python
# Every component logs its actions
INFO: Executing component: rental_data
INFO: Loaded 8019 zip codes with rental data
INFO: Rental price range: $528 - $93333
INFO: Executing component: spatial_join
INFO: Performing spatial join: zip codes -> community areas
INFO: Spatial join resulted in 262 zip-community pairs

# You know EXACTLY what happened at each step
```

**5. Testing & Quality**
```python
# Test individual components in isolation
def test_rental_loader():
    # Arrange
    loader = RentalDataLoader()
    
    # Act
    result = loader.execute({})
    
    # Assert
    assert result.success
    assert "rental_data" in result.data
    assert len(result.data["rental_data"]) > 0

# Test the full pipeline
def test_full_pipeline():
    pipeline = Pipeline("test")
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(SpatialJoinProcessor())
    
    results = pipeline.execute()
    assert all(r.success for r in results)
```

---

### Common Patterns & Use Cases

**Pattern 1: Linear Pipeline (Simple)**
```
Load → Clean → Transform → Analyze → Visualize → Report
```

**Pattern 2: Fan-Out (Parallel Processing)**
```
        ┌→ Analysis A → Viz A ┐
Load →  ├→ Analysis B → Viz B ├→ Combine → Report
        └→ Analysis C → Viz C ┘
```

**Pattern 3: Conditional Execution**
```python
# Skip components based on config
if config.run_advanced_analysis:
    pipeline.register_component(AdvancedAnalyzer())

# Or based on data
class ConditionalComponent(PipelineComponent):
    def execute(self, context):
        if context["data"].shape[0] > 1000:
            # Do expensive analysis
        else:
            # Do quick analysis
```

**Pattern 4: Iterative Refinement**
```
Load → Clean → Analyze → ┐
  ↑                       ↓
  └─── Refine ←──── Validate
```

---

### When NOT to Use a Pipeline

**Pipelines add overhead. Don't use them if:**
- ❌ You have a one-off 10-line script
- ❌ The workflow is completely linear with no reuse
- ❌ You're just exploring data (use notebook first)
- ❌ No collaboration needed (solo project, throwaway code)

**Do use pipelines when:**
- ✅ You have 3+ distinct processing steps
- ✅ Multiple people working on the project
- ✅ Components might be reused elsewhere
- ✅ You need robust error handling
- ✅ The workflow will grow over time
- ✅ You need to test individual parts
- ✅ You want clear logs of what happened

---

### The Chicago Housing Pipeline: A Concrete Example

**The Challenge:**
Rental prices are by ZIP code, but we want analysis by community area.

**Why this needs a pipeline:**
1. **Multiple data sources**: rentals (CSV), ZIP boundaries (CSV/WKT), community boundaries (CSV/WKT)
2. **Complex spatial operations**: ZIP → Community requires area-weighted aggregation
3. **Multiple analyses**: correlation, statistics, visualization
4. **Team collaboration**: different people own different components
5. **Reusability**: spatial join logic used in many projects

**The Pipeline Flow:**
```python
# 1. Data Loading Components
RentalDataLoader()          # Load rental prices by ZIP
  → Returns: {"rental_data": DataFrame}

ZipBoundariesLoader()       # Load ZIP code geometries  
  → Returns: {"zip_boundaries": GeoDataFrame}

CommunityBoundariesLoader() # Load community geometries
  → Returns: {"community_boundaries": GeoDataFrame}

# 2. Processing Component
SpatialJoinProcessor()      # Join rental data across geometries
  → Reads: rental_data, zip_boundaries, community_boundaries
  → Does: Spatial join with area-weighted aggregation
  → Returns: {"community_rental_data": GeoDataFrame}

# 3. Analysis Components  
CorrelationAnalyzer()       # Statistical analysis
  → Reads: community_rental_data
  → Returns: {"correlation_results": dict}

# 4. Visualization Component
CorrelationVisualizer()     # Create plots
  → Reads: correlation_results
  → Returns: {"correlation_plot": matplotlib.Figure}

# 5. Reporting Component
SummaryReporter()           # Generate report
  → Reads: community_rental_data, correlation_results
  → Returns: {"summary_stats": dict}
```

**What makes this powerful:**
- Each component is ~50-100 lines
- Can test spatial join independently
- Can reuse spatial join in other projects
- Can add new analyses without touching existing code
- Team members work on separate components
- Clear logs show exactly what happened

---

## Repository Structure

### Quick Tour
```
src/pipeline/
├── base.py          # Core pipeline architecture (start here!)
├── components.py    # Example components (copy these!)
├── config.py        # Configuration management
└── scripts/         # Usage examples

notebooks/
└── tract_analysis_demo.ipynb  # Interactive demo

tests/
└── test_pipeline_system.py      # Testing examples
```

---

## Three Ways to Create Components

### Decision Guide: Which Method to Use?

**Quick Decision Tree:**
```
Does it load data from a file? 
  → Yes: Use DataLoader

Does it transform/merge data?
  → Yes: Use DataProcessor

Does it do statistical analysis?
  → Yes: Use Analyzer

Does it create visualizations?
  → Yes: Use Visualizer

Is it a simple, one-off function?
  → Yes: Use @pipeline_component decorator

None of the above / need full control?
  → Use PipelineComponent base class
```

---

### Method 1: Inherit from Base Classes (Recommended for most cases)

**When to use:**
- ✅ Your component fits a clear category (load, process, analyze, visualize)
- ✅ You want clear, self-documenting code
- ✅ You're following a standard pattern
- ✅ You want other developers to instantly understand what it does

**Why it's better:**
- Name tells you what it does: `RentalDataLoader` vs `RentalComponent`
- Organized code: all loaders together, all analyzers together
- Easier to test: clear expectations for each type
- Built-in logging: the base classes log automatically

```python
from pipeline.base import DataLoader

class MyDataLoader(DataLoader):
    """Load my custom dataset."""
    
    def __init__(self):
        super().__init__("my_loader", "Loads my data")
    
    def execute(self, context):
        # Your data loading logic here
        data = pd.read_csv("/path/to/data.csv")
        return {"my_data": data}  # Always return a dict!
```

**Four base classes to choose from:**
- `DataLoader` - Load data from files
- `DataProcessor` - Transform/merge data
- `Analyzer` - Statistical analysis
- `Visualizer` - Create plots

### Method 2: Inherit from PipelineComponent (More Flexible)

**When to use:**
- ✅ Your component does something unique (e.g., sends emails, calls APIs, exports data)
- ✅ You need to set custom dependencies
- ✅ You want full control over component behavior
- ✅ You're building something that combines multiple concerns

**Trade-offs:**
- ✅ Pro: Maximum flexibility
- ⚠️ Con: More boilerplate code
- ⚠️ Con: Less self-documenting (need good naming)

**Real-world examples:**
- Sending notification emails after analysis
- Calling external APIs for geocoding
- Exporting results to databases
- Custom caching logic

```python
from pipeline.base import PipelineComponent

class CustomAnalyzer(PipelineComponent):
    def __init__(self):
        super().__init__("custom", "My custom analysis")
        self.dependencies = ["data_loader"]  # What it needs
    
    def execute(self, context):
        # Access data from context
        data = context["my_data"]
        # Do your analysis
        result = data.describe()
        return {"analysis_results": result}
```

### Method 3: Use the @pipeline_component Decorator (Quick & Simple)

**When to use:**
- ✅ You need something quick for prototyping/exploration
- ✅ The logic is simple (< 20 lines)
- ✅ You won't reuse this component elsewhere
- ✅ You're doing a one-time analysis or report

**Trade-offs:**
- ✅ Pro: Fastest to write (just add @decorator)
- ✅ Pro: Great for notebooks and quick scripts
- ⚠️ Con: Harder to test in isolation
- ⚠️ Con: Can't inherit behavior or add methods
- ⚠️ Con: Mixes function and object-oriented styles

**Perfect for:**
- Summary reports
- Quick calculations
- One-off data exports
- Temporary debugging components

**Avoid for:**
- Complex logic that needs testing
- Components you'll maintain long-term
- Anything that needs configuration

```python
from pipeline.base import pipeline_component

@pipeline_component(
    name="quick_analyzer",
    description="Quick analysis function"
)
def analyze_data(context):
    data = context["my_data"]
    return {"mean": data["price"].mean()}
```

---

### Quick Comparison Table

| Criteria | Base Classes | PipelineComponent | Decorator |
|----------|-------------|-------------------|-----------|
| **Best for** | Standard tasks | Custom/unique tasks | Quick prototypes |
| **Code amount** | Medium | Most code | Least code |
| **Clarity** | Highest ⭐⭐⭐ | Medium ⭐⭐ | Lower ⭐ |
| **Flexibility** | Medium | Highest ⭐⭐⭐ | Lowest |
| **Testability** | Easy ⭐⭐⭐ | Easy ⭐⭐⭐ | Harder ⭐ |
| **Maintenance** | Easy ⭐⭐⭐ | Medium ⭐⭐ | Harder ⭐ |
| **Learning curve** | Low | Medium | Low |

---

## Understanding Decorators

### Simple Explanation
```python
# Without decorator (manual)
def my_function():
    return "Hello"

my_function = pipeline_component(name="func")(my_function)

# With decorator (automatic)
@pipeline_component(name="func")
def my_function():
    return "Hello"
```

**The decorator does three things:**
1. Creates a `PipelineComponent` object
2. Sets the name and description
3. Wraps your function so it works with the pipeline

---

## Adding Components to the Pipeline

### Step-by-Step
```python
from pipeline import Pipeline
from pipeline.config import PipelineConfig

# 1. Create the pipeline with config
config = PipelineConfig()
pipeline = Pipeline("My Analysis", config=config)
pipeline.load_config()

# 2. Register your components
pipeline.register_component(MyDataLoader())
pipeline.register_component(MyProcessor())
pipeline.register_component(MyAnalyzer())

# 3. Run it!
results = pipeline.execute()

# 4. Access results from context
final_data = pipeline.context["my_data"]
```

**Important Rules:**
- Always return a dict from `execute()`
- The dict keys become available in `context`
- Components execute in order you register them
- Later components can access earlier results via `context`

---

## Hands-On Example: Building a Component

### In components.py:
```python
from pipeline.base import Analyzer

class QuickStatsAnalyzer(Analyzer):
    """Calculate quick statistics on rental data."""
    
    def __init__(self):
        super().__init__(
            "quick_stats",
            "Calculate mean, median, and std of rental prices"
        )
    
    def execute(self, context):
        data = context["community_rental_data"]
        
        stats = {
            "mean_rent": data["avg_rental_price"].mean(),
            "median_rent": data["avg_rental_price"].median(),
            "std_rent": data["avg_rental_price"].std(),
            "community_count": len(data)
        }
        
        logger.info(f"Calculated stats: {stats}")
        return {"quick_stats": stats}
```

### Use it:
```python
from pipeline.components import QuickStatsAnalyzer

pipeline.register_component(QuickStatsAnalyzer())
results = pipeline.execute()

# Access the results
stats = pipeline.context["quick_stats"]
print(f"Average rent: ${stats['mean_rent']:.2f}")
```

---

## Team Collaboration - Avoiding Merge Conflicts

### The Problem: Everyone Editing components.py

If everyone edits the same `components.py` file, you'll have merge conflicts constantly.

### Solution: One Component Per File

**File Structure for Team Projects:**
```
src/pipeline/
├── base.py                    # Don't touch! (core pipeline)
├── config.py                  # Don't touch! (configuration)
│
├── components/                # New folder for components
│   ├── __init__.py           # Import everything here
│   ├── loaders.py            # All data loaders
│   ├── processors.py         # All data processors
│   ├── analyzers.py          # All analyzers
│   ├── visualizers.py        # All visualizers
│   │
│   # OR even more granular:
│   ├── rental_loader.py      # One person owns this
│   ├── spatial_join.py       # Another person owns this
│   └── correlation_viz.py    # Another person owns this
```

### Strategy 1: By Component Type (Good for small teams)

**`components/loaders.py`:**
```python
from pipeline.base import DataLoader

class RentalDataLoader(DataLoader):
    # Person A works here
    pass

class ZipBoundariesLoader(DataLoader):
    # Person B works here
    pass
```

**`components/__init__.py`:**
```python
# Import everything so it's easy to use
from .loaders import RentalDataLoader, ZipBoundariesLoader
from .processors import SpatialJoinProcessor
from .analyzers import CorrelationAnalyzer

__all__ = [
    "RentalDataLoader",
    "ZipBoundariesLoader", 
    "SpatialJoinProcessor",
    "CorrelationAnalyzer",
]
```

**Then use it normally:**
```python
from pipeline.components import RentalDataLoader  # Works the same!
```

### Strategy 2: One File Per Component (Best for larger teams)

**Each person gets their own file:**
```
components/
├── __init__.py
├── alice_rental_loader.py     # Alice owns this
├── bob_spatial_join.py         # Bob owns this
├── carol_correlation.py        # Carol owns this
└── david_visualizer.py         # David owns this
```

**Benefits:**
- ✅ Zero merge conflicts on component code
- ✅ Clear ownership (each person has their file)
- ✅ Easy to review (small, focused PRs)
- ✅ Can work in parallel without coordination

### Strategy 3: Feature-Based Modules (Best for complex projects)

**Organize by analysis feature:**
```
components/
├── __init__.py
├── rental_analysis/
│   ├── __init__.py
│   ├── loader.py
│   ├── processor.py
│   └── analyzer.py
│
├── spatial_analysis/
│   ├── __init__.py
│   ├── spatial_join.py
│   └── area_calculator.py
│
└── visualization/
    ├── __init__.py
    ├── correlation_plots.py
    └── map_visualizer.py
```

### Quick Migration Guide

**Step 1: Create the structure**
```bash
mkdir -p src/pipeline/components
touch src/pipeline/components/__init__.py
```

**Step 2: Move one component**
```python
# In components/rental_loader.py
from pipeline.base import DataLoader

class RentalDataLoader(DataLoader):
    # ... your code here
```

**Step 3: Export it**
```python
# In components/__init__.py
from .rental_loader import RentalDataLoader

__all__ = ["RentalDataLoader"]
```

**Step 4: Update imports in your scripts**
```python
# Old way (still works for now)
from pipeline.components import RentalDataLoader

# New way (same result!)
from pipeline.components import RentalDataLoader
```

### Team Workflow Best Practices

**1. Assign Component Ownership**
```
Components owned by:
- Alice: RentalDataLoader, HousingDataLoader
- Bob: SpatialJoinProcessor, AreaCalculator  
- Carol: CorrelationAnalyzer, StatisticsAnalyzer
- David: All visualizers
```

**2. Use Branch Naming Convention**
```bash
git checkout -b feature/alice-rental-loader
git checkout -b feature/bob-spatial-join
```

**3. Small, Focused PRs**
- ✅ One component per PR
- ✅ Include tests for your component
- ✅ Update `__init__.py` in the same PR

**4. Parallel Development Flow**
```
Day 1: 
- Alice creates rental_loader.py
- Bob creates spatial_join.py
- No conflicts!

Day 2:
- Alice: PR for rental_loader.py
- Bob: PR for spatial_join.py  
- They can be merged independently!
```

### Pro Tips

**Avoid conflicts in `__init__.py`:**
```python
# Instead of listing everything:
from .rental_loader import RentalDataLoader
from .spatial_join import SpatialJoinProcessor
# ... (gets messy with many components)

# Use this pattern:
from .rental_loader import *
from .spatial_join import *
from .analyzers import *

# Each file defines __all__:
# In rental_loader.py:
__all__ = ["RentalDataLoader"]
```

**Testing isolated components:**
```python
# In tests/components/test_rental_loader.py
from pipeline.components.rental_loader import RentalDataLoader

# Each person tests their own component
# No conflicts in test files either!
```

**Communication is key:**
- 📢 Announce when you're working on a component
- 📢 Coordinate on shared dependencies
- 📢 Review each other's PRs quickly
- 📢 Merge frequently to avoid drift

---

## Key Takeaways

### The Three-Step Recipe:
1. **Choose your approach**: Base class, PipelineComponent, or decorator
2. **Write execute() method**: Takes `context`, returns `dict`
3. **Register and run**: Add to pipeline, call `execute()`

### Pro Tips:
- ✅ Use descriptive names for your components
- ✅ Always return a dict with clear keys
- ✅ Use `logger.info()` to track what's happening
- ✅ Look at existing components as templates
- ✅ Test with small data first
- ✅ **One component per file = zero merge conflicts!**

### Where to Start:
1. **Copy an existing component** from `components.py`
2. **Modify the execute() method** for your needs
3. **Test it** in the notebook or with pytest

---

## Frequently Asked Questions

**How do I know what's in context?**

Print `pipeline.context.keys()` or look at what previous components returned.

**Can components fail gracefully?**

Yes! Wrap your code in try/except, the pipeline catches errors and continues.

**How do I access configuration?**

Use `self.config` in components, or access `pipeline.pipeline_config`.

**What about dependencies between components?**

Set `self.dependencies = ['component_name']` - pipeline handles ordering automatically.

**How do I test my component?**

Look at `tests/test_pipeline_system.py` - use arrange-act-assert pattern.

---

## Additional Resources

**Example Code:**
- `notebooks/tract_analysis_demo.ipynb` - Interactive pipeline demonstration
- `src/pipeline/scripts/pipeline_usage.py` - Example usage scripts
- `tests/test_pipeline_system.py` - Testing examples

**Key Files:**
- `src/pipeline/base.py` - Core architecture
- `src/pipeline/components.py` - Example components  
- `src/pipeline/config.py` - Configuration system
- `README.md` - Setup and usage documentation

