# 2025-autumn-city-of-chicago-housing

## Project Background
The Department of Technology and Innovation (DTI) is the City of Chicago’s central IT
agency. DTI manages the City’s core technology infrastructure, digital services, data
management, data analytics, and applied data science. Our data team applies data science
and advanced analytics, including model development, forecasting, and pattern detection,
to strengthen decision-making, improve service delivery, and build more accessible,
resident-centered digital tools.

This project will investigate the relationship between affordable housing, short-term rental (STR) restrictions, and foreclosure activity in Chicago. Using publicly available datasets from the City of Chicago and supplemental socioeconomic indicators, the project will analyze how housing pressures vary across community areas.

The analysis will emphasize data wrangling, exploratory analysis, clustering, and predictive modeling, with visualization used to support insights rather than as a standalone deliverable.

Key questions include:
- Do neighborhoods with high STR restrictions differ systematically from those without restrictions in terms of affordability and foreclosure activity?
- Can clustering techniques reveal distinct “neighborhood types” based on housing and socioeconomic conditions?
- Can predictive modeling estimate the likelihood of a community area experiencing housing pressure—defined as an increased risk of affordability challenges due to overlapping factors such as STR restrictions, foreclosure rates, and limited affordable housing?


## Project Goals

1. Cleaned and Integrated Dataset
    - Merge Affordable Rental Housing Developments, STR Prohibited Buildings, Foreclosed Rental Properties, and Census socioeconomic indicators at the community area level.
    - Standardize variables (e.g., proportions, normalized indicators) for analysis.
2. Exploratory Data Analysis (EDA)
    - Descriptive statistics and correlation analysis across datasets.
    - Visualizations (scatterplots, bar charts, heatmaps, static choropleths) to highlight patterns and relationships between STR restrictions, affordable housing, and foreclosures.
3. Clustering Analysis
    - Apply clustering methods (k-means, hierarchical clustering) to group community areas based on housing and socioeconomic characteristics.
    - Evaluate clusters with silhouette scores or gap statistics.
    - Interpret clusters as different neighborhood types (e.g., high STR restrictions + low affordability vs. low restrictions + higher foreclosure rates).
4. Predictive Modeling
    - Build predictive models (logistic regression, random forest, gradient boosting) to estimate the likelihood of a community area becoming a housing pressure zone.
    - Validate models using cross-validation and evaluate performance (ROC-AUC, precision/recall).
    - Analyze feature importance to determine which factors most strongly influence housing pressure.
5. Final Report
    - Synthesize findings from EDA, clustering, and modeling into a clear narrative.
    - Present visualizations that highlight key results.
    - Provide evidence-based insights for anticipating and addressing housing challenges.

## Data
- [Chicago’s Affordable Rental Housing Developments](https://data.cityofchicago.org/Community-Economic-Development/Affordable-Rental-Housing-Developments/s6ha-ppgi/about_data): Thousands of affordable units that are supported by City of Chicago programs to maintain affordability in local neighborhoods. Includes location data, management companies, and number of units
- [House Share Prohibited Buildings List](https://data.cityofchicago.org/Buildings/House-Share-Prohibited-Buildings-List/7bzs-jsyj/about_data): A list of buildings excluded from short-term rental activity under the Shared Housing Ordinance. Includes location data, number of units, and dates.
- [Foreclosed Rental Properties dataset](https://data.cityofchicago.org/Community-Economic-Development/Foreclosed-Rental-Property/yhcw-iu53/about_data): Foreclosed rental properties registered with the Chicago Department of Housing under the Keep Chicago Renting ordinance. Includes owner information, address, date, previous notices, and management names.
- [Zillow Observed Rent Index (ZORI)](https://www.zillow.com/research/data/): available by zip code
- [Chicago Spatial Datasets](https://guides.lib.uchicago.edu/c.php?g=720045&p=8072546): links to base layers for community areas and zip code boundaries
- [American Community Survey Data](https://www.census.gov/programs-surveys/acs/data.html)


## The Pipeline: Census Tract-Level Analysis

This pipeline demonstrates spatial analysis at the **census tract level** for fine-grained neighborhood analysis:

### Data Sources
- **Rental Data**: CSV with zip codes and rental prices (ZORI dataset)
- **Zip Boundaries**: CSV with WKT polygon strings for zip code boundaries  
- **Census Tract Boundaries**: CSV with WKT polygon strings for tract boundaries

### Key Capabilities
- **Zip-to-Tract Mapping**: Handles many-to-many relationships with area-weighted aggregation
- **Tract-to-Community Aggregation**: Clean hierarchical aggregation from tracts to neighborhoods
- **Spatial Joins**: Transforms data from zip codes (postal) to census tracts (statistical)
- **Crosswalk Creation**: Generates reusable zip-to-tract mapping with intersection weights
- **Multi-Level Analysis**: Analyze at tract level (800+ areas) OR aggregate to community level (77 areas)

### Why Census Tracts as the Base Unit?
- **Standardized**: Consistent boundaries across the entire US
- **Census-aligned**: Easy to join with ACS demographic data
- **Fine-grained**: ~4,000 residents per tract vs ~35,000 per community area
- **Equity analysis**: Detect block-level disparities that larger geographies mask
- **Hierarchical**: Designed to aggregate up to counties, communities, etc.

## Pipeline Architecture

The system uses a modular pipeline architecture with two main packages:

### Generic Pipeline Framework (`src/pipeline/`)
A reusable, domain-agnostic framework for building data analysis pipelines:
- **Base Classes**: `Pipeline`, `DataLoader`, `DataProcessor`, `Analyzer`, `Visualizer`
- **Configuration System**: YAML/JSON config files with environment variable support
- **Pipeline Orchestrator**: Manages component execution and shared context
- **Error Handling**: Robust error handling and validation

### Housing Components (`src/housing/`)
Chicago housing-specific analysis components organized by type:
- **Loaders** (`components/loaders/`): RentalDataLoader, ZipBoundariesLoader, CommunityBoundariesLoader, TractBoundariesLoader
- **Processors** (`components/processors/`): ZipToTractProcessor, TractToCommunityProcessor
- **Analyzers** (`components/analyzers/`): CorrelationAnalyzer, TractAnalyzer
- **Visualizers** (`components/visualizers/`): CorrelationVisualizer
- **Scripts** (`scripts/`): Complete housing analysis workflows

### Key Features
- **Modular Design**: Each component in its own file for independent development
- **Professional Logging**: Structured logging throughout
- **Flexible Configuration**: Environment-based configuration
- **Reusable Framework**: Generic pipeline can be used for any domain


## Quick Start

### 1. Setup Environment
```bash
# Clone the repository
git clone <repository-url> spatial-data-analysis-pipeline
cd spatial-data-analysis-pipeline

# Copy the example environment file
cp .env.example .env

# Edit .env to set your data directory path
# Example: DATA_DIR=/Users/yourname/project/data
```

### 2. Choose Your Development Workflow

#### Option A: Development Container (Recommended)
**Best for**: Interactive development, notebooks, and full IDE integration

```bash
# Build the devcontainer
make devcontainer

# Open in VS Code or Cursor
# When prompted, click "Reopen in Container"
```

**Benefits**:
- Run notebooks directly in the editor
- Full IDE integration with code completion
- Pre-configured Python environment
- All extensions and tools ready to use

#### Option B: Command Line with Make
**Best for**: Scripts, testing, and automated workflows

```bash
# Install pre-commit hooks
make run-interactive
# Inside container:
pre-commit install
exit

# Test your setup
make test-pipeline
```

### 3. Run the Pipeline Demos

**Housing EDA Pipeline** (Complete spatial analysis):
```bash
# Outside the container
make test-pipeline

# Inside the container 
uv run python src/housing/scripts/housing_eda_pipeline.py
```

**Generic Pipeline Demo** (Framework examples):
```bash
# Outside the container
make test-generic-pipeline

# Inside the container
uv run python src/pipeline/scripts/pipeline_usage.py
```

The housing pipeline generates:
- Processed data with spatial joins at multiple geographic levels
- Correlation analysis results
- Visualization plots
- Summary reports

### 4. Explore the Notebook

Open `notebooks/tract_analysis_demo.ipynb` to see the complete tract-level analysis workflow:
- Zip code to census tract spatial joins
- Area-weighted aggregation
- Crosswalk creation
- Tract-level statistical analysis

**For detailed instructions on obtaining tract data**, see `CENSUS_TRACT_GUIDE.md`

## Technical Expectations

### Container-Based Development

**All code must be run inside the Docker container.** This ensures consistent environments across different machines and eliminates "works on my machine" issues.

**Important**: When running Python code inside the container, prefix commands with `uv run` to maintain the proper environment:

```bash
# Example: Running the housing pipeline
uv run python src/housing/scripts/housing_eda_pipeline.py

# Example: Running tests
uv run pytest tests/
```

## Usage & Examples

### Working with the Pipeline System

The project is organized into two main packages:

**Generic Pipeline Framework** (`src/pipeline/`):
```
src/pipeline/
├── __init__.py           # Base classes export
├── base.py              # Abstract base classes
├── config.py            # Configuration management
└── scripts/
    └── pipeline_usage.py    # Generic framework demo
```

**Housing Components** (`src/housing/`):
```
src/housing/
├── __init__.py           # Housing components export
├── components/
│   ├── loaders/         # Data loading components
│   ├── processors/      # Spatial processing components
│   ├── analyzers/       # Statistical analysis components
│   ├── visualizers/     # Visualization components
│   ├── constants.py     # Shared constants
│   └── utils.py         # Utility functions
└── scripts/
    └── housing_eda_pipeline.py  # Complete housing workflow
```

### Basic Pipeline Usage

**Import and Use Components**:
```python
# Import pipeline framework
from pipeline import Pipeline
from pipeline.config import PipelineConfig

# Import housing components
from housing import (
    RentalDataLoader,
    ZipBoundariesLoader,
    CommunityBoundariesLoader,
    ZipToTractProcessor,
    TractAnalyzer,
    CorrelationVisualizer,
)

# Create pipeline with configuration
config = PipelineConfig()
pipeline = Pipeline("My Analysis", config=config)
pipeline.load_config()

# Register housing components
pipeline.register_component(RentalDataLoader())
pipeline.register_component(ZipBoundariesLoader())
pipeline.register_component(CommunityBoundariesLoader())
pipeline.register_component(ZipToTractProcessor())
pipeline.register_component(TractAnalyzer())

# Execute pipeline
results = pipeline.execute()
```

**Run Example Scripts**:
```bash
# Run the housing analysis pipeline
uv run python src/housing/scripts/housing_eda_pipeline.py

# Run the generic framework demo
uv run python src/pipeline/scripts/pipeline_usage.py
```

### Configuration Management

The pipeline uses a flexible configuration system:

```python
# Use default configuration
config = PipelineConfig()

# Load from YAML file
from pipeline.config import ConfigManager
config_manager = ConfigManager("config/pipeline_config.yaml")
config = config_manager.load_config()

# Create custom configuration
config = PipelineConfig()
config.data.rental_data_path = Path("/custom/path/data.csv")
```

### Data Management

- Set `DATA_DIR` in your `.env` file to specify where data lives on your host
- This directory is mounted to `/project/data` inside the container
- Keep data separate from code to avoid repository bloat and enable easy data sharing
- The pipeline automatically validates data file existence 


### Docker & Make Commands

We use `docker` and `make` to run our code. Available `make` commands:

* `make help`: Show all available commands and descriptions
* `make build-only`: Build the Docker image only
* `make devcontainer`: Build and prepare devcontainer for VS Code/Cursor
* `make run-interactive`: Create a container and load an interactive bash session
* `make test`: Run all tests with pytest
* `make test-pipeline`: Run the housing EDA pipeline
* `make test-generic-pipeline`: Run the generic pipeline framework demo
* `make clean`: Clean up Docker images and containers

**Note**: For notebook development, use the devcontainer workflow instead of command-line tools for the best experience.

The file `Makefile` contains details about the specific commands that are run when calling each `make` target.

## Documentation

Comprehensive guides are available:

* **PIPELINE_GUIDE.md**: Complete guide to the pipeline framework architecture
* **COMPONENT_STRUCTURE.md**: Details on the component directory structure
* **STUDENT_GUIDE.md**: Step-by-step guide for creating new components
* **CENSUS_TRACT_GUIDE.md**: Guide to census tract-level analysis


## Style
We use [`ruff`](https://docs.astral.sh/ruff/) to enforce style standards and grade code quality. This is an automated code checker that looks for specific issues in the code that need to be fixed to make it readable and consistent with common standards. `ruff` is run before each commit via [`pre-commit`](https://pre-commit.com/). If it fails, the commit will be blocked and the user will be shown what needs to be changed.

Once you have followed the quick setup instructions above for installing dependencies, you can run:
```bash
pre-commit run --all-files
```

You can also run `ruff` directly:
```bash
ruff check
ruff format
```