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

### Primary Datasets
- [Chicago's Affordable Rental Housing Developments](https://data.cityofchicago.org/Community-Economic-Development/Affordable-Rental-Housing-Developments/s6ha-ppgi/about_data): Thousands of affordable units that are supported by City of Chicago programs to maintain affordability in local neighborhoods. Includes location data, management companies, and number of units
- [House Share Prohibited Buildings List](https://data.cityofchicago.org/Buildings/House-Share-Prohibited-Buildings-List/7bzs-jsyj/about_data): A list of buildings excluded from short-term rental activity under the Shared Housing Ordinance. Includes location data, number of units, and dates.
- [Foreclosed Rental Properties dataset](https://data.cityofchicago.org/Community-Economic-Development/Foreclosed-Rental-Property/yhcw-iu53/about_data): Foreclosed rental properties registered with the Chicago Department of Housing under the Keep Chicago Renting ordinance. Includes owner information, address, date, previous notices, and management names.
- [Zillow Observed Rent Index (ZORI)](https://www.zillow.com/research/data/): Available by ZIP code
- [American Community Survey Data](https://www.census.gov/programs-surveys/acs/data.html): Census demographic and socioeconomic data

### Spatial Boundary Data
The pipeline uses three levels of geographic boundaries for spatial analysis:

**Census Tracts** (Fine-grained, ~1,300 tracts in Cook County):
- **Source**: [2023 TIGER/Line Shapefiles](https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2023&layergroup=Census+Tracts)
- **Location**: Extract `tl_2023_17_tract.zip` to `data/tl_2023_17_tract/`
- **Why**: Standardized statistical boundaries aligned with Census data; ideal for detecting fine-grained neighborhood patterns

**Community Areas** (77 neighborhoods):
- **Source**: [Chicago Data Portal API](https://data.cityofchicago.org/resource/igwz-8jzy.json)
- **Location**: Automatically fetched and cached to `data/.cache/community_boundaries.json`
- **Why**: Official Chicago neighborhood boundaries used for planning and reporting

**ZIP Codes** (59 postal zones):
- **Source**: [Chicago Data Portal API](https://data.cityofchicago.org/resource/unjd-c2ca.json)
- **Location**: Automatically fetched and cached to `data/.cache/zip_boundaries.json`
- **Why**: Bridge between postal-based data (e.g., rental prices) and statistical boundaries

**Note**: API responses are automatically cached locally after the first fetch, making subsequent pipeline runs much faster and reducing load on the Chicago Data Portal servers.


## Pipeline Overview

This pipeline performs spatial analysis at the **census tract level** for fine-grained neighborhood analysis. Census tracts (~1,300 in Cook County) provide standardized, census-aligned boundaries that are ideal for detecting neighborhood patterns and joining with demographic data.

The pipeline transforms data through a spatial hierarchy:
1. **ZIP codes** (postal boundaries) → **Census tracts** (statistical boundaries)
2. **Census tracts** → **Community areas** (Chicago neighborhoods)

This enables both fine-grained tract-level analysis and aggregated community-level insights.

**For detailed technical information**, see:
- `docs/CENSUS_TRACT_GUIDE.md` - Spatial aggregation methodology
- `docs/TRACT_TO_COMMUNITY_GUIDE.md` - Tract to community area aggregation
- `docs/PIPELINE_GUIDE.md` - Pipeline architecture and components

## Architecture

The codebase is organized into two main packages:

**Generic Pipeline Framework** (`src/pipeline/`):
- Reusable, domain-agnostic framework for data analysis pipelines
- Base classes: `Pipeline`, `DataLoader`, `DataProcessor`, `Analyzer`, `Visualizer`
- YAML/JSON configuration with environment variable support

**Housing Components** (`src/housing/`):
- Chicago-specific analysis components
- Organized by type: loaders, processors, analyzers, visualizers, scripts
- Implements the spatial aggregation workflow

### Design Considerations
- **Modularity**: Each component is independently developed and testable
- **Separation of concerns**: Generic framework vs. domain-specific logic
- **Configuration-driven**: Data paths and parameters externalized
- **Logging**: Structured logging throughout for debugging and monitoring


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

### 2. Prepare Data Files

**Required: Census Tract Boundaries**
1. Download [2023 TIGER/Line Illinois Census Tracts](https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_17_tract.zip)
2. Extract to your data directory:
   ```bash
   # Option A - Command line
   unzip tl_2023_17_tract.zip -d data/tl_2023_17_tract/
   
   # Option B - GUI (easier)
   # Move zip to data/ folder and double-click to extract
   ```
3. Result: All shapefile components in `data/tl_2023_17_tract/`

**Required: Rental Price Data**
- Download ZORI data and place in `data/Zip_zori_uc_sfrcondomfr_sm_month.csv`

**Automatic: Boundary APIs**
- Community and ZIP boundaries are fetched automatically from Chicago Data Portal
- Cached to `data/.cache/` on first run for faster subsequent runs
- No manual download needed!

See `docs/CENSUS_TRACT_GUIDE.md` for detailed instructions.

### 3. Choose Your Development Workflow

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
make test
```

### 4. Run the Pipeline Demos

**Housing EDA Pipeline** (Complete spatial analysis):
```bash
# Outside the container
make run-eda-pipeline

# Inside the container 
uv run python src/housing/scripts/housing_eda_pipeline.py
```

**Generic Pipeline Demo** (Framework examples):
```bash
# Outside the container
make run-generic-pipeline

# Inside the container
uv run python src/pipeline/scripts/pipeline_usage.py
```

The housing pipeline generates:
- Processed data with spatial joins at multiple geographic levels
- Correlation analysis results
- Visualization plots
- Summary reports

### 5. Explore the Notebook

Open `notebooks/tract_analysis_demo.ipynb` to see the complete tract-level analysis workflow:
- Zip code to census tract spatial joins
- Area-weighted aggregation
- Crosswalk creation
- Tract-level statistical analysis

**For detailed instructions on obtaining tract data**, see `docs/CENSUS_TRACT_GUIDE.md`

## Development

**All code must run inside the Docker container** to ensure consistent environments. Prefix Python commands with `uv run`:

```bash
# Run analysis pipelines
uv run python src/housing/scripts/housing_eda_pipeline.py
uv run python src/pipeline/scripts/pipeline_usage.py

# Run tests
uv run pytest tests/
```

### Creating New Components

See `docs/STUDENT_GUIDE.md` for step-by-step instructions on:
- Creating loaders, processors, analyzers, and visualizers
- Registering components in the pipeline
- Common patterns and best practices

### Configuration

The pipeline uses YAML configuration files with environment variable support. Configuration includes:
- Data file paths (can be local files or URLs)
- Analysis parameters
- Component execution order

See `docs/PIPELINE_GUIDE.md` for configuration details and `config/pipeline_config.yaml` for examples.

### Data Management

- Set `DATA_DIR` in your `.env` file to specify where data lives on your host
- This directory is mounted to `/project/data` inside the container
- Keep data separate from code to avoid repository bloat and enable easy data sharing
- The pipeline automatically validates data file existence

**Data Directory Structure**:
```
data/
├── .cache/                                  # Auto-generated API caches
│   ├── community_boundaries.json           # Community areas (2.1 MB)
│   └── zip_boundaries.json                 # ZIP codes (1.5 MB)
├── tl_2023_17_tract/                       # Census tract shapefiles
│   ├── tl_2023_17_tract.shp               # Main shapefile
│   ├── tl_2023_17_tract.shx               # Shape index
│   ├── tl_2023_17_tract.dbf               # Attributes
│   ├── tl_2023_17_tract.prj               # Projection
│   └── tl_2023_17_tract.cpg               # Character encoding
└── Zip_zori_uc_sfrcondomfr_sm_month.csv   # Rental price data
```

**Cache Management**:
- API responses are automatically cached after first fetch
- To refresh cached data: `rm -rf data/.cache/`
- Cache files are gitignored (inside `data/`) 


### Make Commands

Common commands (run `make help` for full list):

* `make devcontainer` - Build devcontainer for VS Code/Cursor
* `make run-interactive` - Interactive bash session in container
* `make test` - Run all tests
* `make run-eda-pipeline` - Run housing analysis pipeline
* `make clean` - Clean up Docker artifacts

See `Makefile` for implementation details.

### Code Quality

We use [`ruff`](https://docs.astral.sh/ruff/) for code formatting and linting, enforced via [`pre-commit`](https://pre-commit.com/) hooks:

```bash
# Run all checks
pre-commit run --all-files

# Or run ruff directly
ruff check
ruff format
```

## Documentation

- **docs/PIPELINE_GUIDE.md** - Pipeline framework architecture
- **docs/CENSUS_TRACT_GUIDE.md** - Spatial aggregation methodology
- **docs/TRACT_TO_COMMUNITY_GUIDE.md** - Tract to community area aggregation
- **docs/STUDENT_GUIDE.md** - Creating new components
- **docs/COMPONENT_STRUCTURE.md** - Directory structure reference