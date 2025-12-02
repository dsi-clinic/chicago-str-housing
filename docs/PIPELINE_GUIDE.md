# Pipeline Framework Guide

This guide covers the generic pipeline framework (`src/pipeline/`) - a reusable, domain-agnostic system for building data analysis workflows. The framework can be used for any type of data processing project.

## Overview

The pipeline framework provides a structured approach to data analysis by breaking complex workflows into reusable, testable components. Components share data through a context dictionary and execute in a coordinated sequence.

## Core Concepts

### Pipeline Architecture

```python
from pipeline import Pipeline, DataLoader, DataProcessor, Analyzer, Visualizer

# Create a pipeline
pipeline = Pipeline("My Analysis Pipeline")

# Register components
pipeline.register_component(MyDataLoader())
pipeline.register_component(MyProcessor())
pipeline.register_component(MyAnalyzer())
pipeline.register_component(MyVisualizer())

# Execute
results = pipeline.execute()
```

### Component Types

The framework provides four base component types:

| Type | Purpose | When to Use |
|------|---------|-------------|
| **DataLoader** | Load data from files, APIs, databases | First step in any pipeline |
| **DataProcessor** | Transform, aggregate, or clean data | Between loading and analysis |
| **Analyzer** | Perform statistical analysis | After data is prepared |
| **Visualizer** | Create plots, maps, reports | Final step for outputs |

### Context (Shared Memory)

Components communicate through a shared context dictionary:

```python
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    # Read from context
    input_data = context.get("previous_data")
    
    # Process
    processed = self.process(input_data)
    
    # Write to context
    return {"processed_data": processed}
```

The pipeline automatically updates the context after each component executes, making data available to subsequent components.

## Creating Components

### Component Template

All components inherit from base classes and implement the `execute` method:

```python
from pipeline.base import DataLoader
from typing import Any
import logging

logger = logging.getLogger(__name__)

class MyDataLoader(DataLoader):
    def __init__(self, file_path: str | None = None) -> None:
        super().__init__(
            name="my_data",  # Key in context
            file_path=file_path or "/path/to/data.csv",
            description="Load my data"
        )
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("Loading data from %s", self.file_path)
        
        # Load your data
        data = pd.read_csv(self.file_path)
        
        # Return dictionary (key becomes available in context)
        return {"my_data": data}
```

### DataLoader Example

```python
class CSVLoader(DataLoader):
    def __init__(self, file_path: str) -> None:
        super().__init__("csv_data", file_path, "Load CSV file")
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        df = pd.read_csv(self.file_path)
        return {"csv_data": df}
```

### DataProcessor Example

```python
class DataProcessor(DataProcessor):
    def __init__(self) -> None:
        super().__init__("cleaner", "Clean and transform data")
        self.required_data = ["csv_data"]  # Declare dependencies
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        df = context["csv_data"]
        
        # Clean data
        df_clean = df.dropna().reset_index(drop=True)
        
        return {"cleaned_data": df_clean}
```

### Analyzer Example

```python
class CorrelationAnalyzer(Analyzer):
    def __init__(self) -> None:
        super().__init__("correlation", "Calculate correlations")
        self.required_data = ["cleaned_data"]
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        df = context["cleaned_data"]
        corr_matrix = df.corr()
        return {"correlations": corr_matrix}
```

### Visualizer Example

```python
class PlotVisualizer(Visualizer):
    def __init__(self) -> None:
        super().__init__("plotter", "Create visualizations")
        self.required_data = ["cleaned_data"]
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        df = context["cleaned_data"]
        
        # Create plot
        fig, ax = plt.subplots()
        df.plot(ax=ax)
        plt.savefig("output/plot.png")
        
        return {}  # No data to add to context
```

## Pipeline Execution

### Automatic Execution Order

The pipeline automatically determines execution order based on dependencies:

```python
pipeline = Pipeline("My Pipeline")
pipeline.register_component(DataLoader())
pipeline.register_component(Processor())  # Depends on loader
pipeline.register_component(Analyzer())   # Depends on processor
pipeline.register_component(Visualizer())  # Depends on analyzer

results = pipeline.execute()  # Executes in correct order
```

### Manual Execution Order

You can also specify execution order explicitly:

```python
pipeline.set_execution_order([
    "data_loader",
    "processor",
    "analyzer",
    "visualizer"
])
results = pipeline.execute()
```

### Accessing Results

After execution, access results through the pipeline context:

```python
results = pipeline.execute()

# Access final data
final_data = pipeline.context["processed_data"]

# Access execution results
for result in pipeline.results:
    print(f"{result.component_name}: {result.success} ({result.execution_time:.2f}s)")
```

## Component Dependencies

Components can declare dependencies to ensure proper execution order:

```python
class MyProcessor(DataProcessor):
    def __init__(self) -> None:
        super().__init__("processor", "Process data")
        self.required_data = ["input_data"]  # Must exist in context
        self.dependencies = ["loader"]        # Component must run first
```

The pipeline validates dependencies before execution and raises errors if requirements aren't met.

## Configuration

Pipelines support YAML/JSON configuration files:

```yaml
data:
  input_path: "/path/to/data.csv"
  output_dir: "/path/to/output"

analysis:
  parameters:
    threshold: 0.5
    method: "standard"

components:
  - "loader"
  - "processor"
  - "analyzer"
```

Load configuration:

```python
pipeline = Pipeline("My Pipeline")
pipeline.load_config("config.yaml")
```

## Error Handling

Components should handle errors gracefully:

```python
def execute(self, context: dict[str, Any]) -> dict[str, Any]:
    try:
        data = context["required_data"]
        result = self.process(data)
        return {"output": result}
    except KeyError:
        logger.error("Required data not found in context")
        return {}  # Return empty dict on error
    except Exception as e:
        logger.error("Processing failed: %s", e)
        return {}
```

The pipeline continues execution even if individual components fail, allowing you to inspect results and debug issues.

## Best Practices

1. **Declare Dependencies**: Use `required_data` and `dependencies` to make component relationships explicit
2. **Use Logging**: Log important steps with `logger.info()`, `logger.warning()`, `logger.error()`
3. **Return Clear Keys**: Use descriptive dictionary keys that indicate what data is being provided
4. **Handle Missing Data**: Check for required context keys before accessing them
5. **Keep Components Focused**: Each component should do one thing well
6. **Make Components Reusable**: Design components to work with different data sources when possible

## Example: Complete Pipeline

```python
from pipeline import Pipeline, DataLoader, DataProcessor, Analyzer
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Define components
class SalesDataLoader(DataLoader):
    def __init__(self):
        super().__init__("sales", "/data/sales.csv", "Load sales data")
    
    def execute(self, context):
        df = pd.read_csv(self.file_path)
        return {"sales": df}

class SalesCleaner(DataProcessor):
    def __init__(self):
        super().__init__("cleaner", "Clean sales data")
        self.required_data = ["sales"]
    
    def execute(self, context):
        df = context["sales"]
        df_clean = df.dropna()
        return {"sales_clean": df_clean}

class SalesAnalyzer(Analyzer):
    def __init__(self):
        super().__init__("analyzer", "Analyze sales")
        self.required_data = ["sales_clean"]
    
    def execute(self, context):
        df = context["sales_clean"]
        summary = df.groupby("category").sum()
        return {"summary": summary}

# Build and run pipeline
pipeline = Pipeline("Sales Analysis")
pipeline.register_component(SalesDataLoader())
pipeline.register_component(SalesCleaner())
pipeline.register_component(SalesAnalyzer())

results = pipeline.execute()

# Access results
summary = pipeline.context["summary"]
print(summary)
```

This framework provides a foundation for building maintainable, testable data analysis workflows that can be adapted to any domain or data type.
