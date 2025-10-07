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


## First Week
- Download and map the Affordable Housing Developments, House Share Prohibited, Foreclosed Rental Properties, and ZORI datasets
- Download tract-level population and socioeconomic indicators for Cook County
- Develop a strategy to aggregate the tract-level data to the community area level and merge it with the City of Chicago data 
- Complete the quick start below, making sure that you can find the file `sample_output.csv`.


## Data
- [Chicago’s Affordable Rental Housing Developments](https://data.cityofchicago.org/Community-Economic-Development/Affordable-Rental-Housing-Developments/s6ha-ppgi/about_data): Thousands of affordable units that are supported by City of Chicago programs to maintain affordability in local neighborhoods. Includes location data, management companies, and number of units
- [House Share Prohibited Buildings List](https://data.cityofchicago.org/Buildings/House-Share-Prohibited-Buildings-List/7bzs-jsyj/about_data): A list of buildings excluded from short-term rental activity under the Shared Housing Ordinance. Includes location data, number of units, and dates.
- [Foreclosed Rental Properties dataset](https://data.cityofchicago.org/Community-Economic-Development/Foreclosed-Rental-Property/yhcw-iu53/about_data): Foreclosed rental properties registered with the Chicago Department of Housing under the Keep Chicago Renting ordinance. Includes owner information, address, date, previous notices, and management names.
- [Zillow Observed Rent Index (ZORI)](https://www.zillow.com/research/data/): available by zip code
- [Chicago Spatial Datasets](https://guides.lib.uchicago.edu/c.php?g=720045&p=8072546): links to base layers for community areas and zip code boundaries
- [American Community Survey Data](https://www.census.gov/programs-surveys/acs/data.html)


## Quick Start

### 1. Setup Environment
```bash
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

### 3. Test Your Setup
```bash
# If using devcontainer: Open a notebook and run cells
# If using make: Run the pipeline test
make test-pipeline
```

If successful, you should see `sample_output.csv` appear in your data directory.

## Technical Expectations

### Pre requisites:

We use Docker, Make and uv as part of our curriculum. If you are unfamiliar with them, it is strongly recommended you read over the following:
- [An introduction to Docker](https://docker-curriculum.com/)
- [An introduction to uv](https://realpython.com/python-uv/)

### Container-Based Development

**All code must be run inside the Docker container.** This ensures consistent environments across different machines and eliminates "works on my machine" issues.

### Environment Management with uv

We use [uv](https://docs.astral.sh/uv/) for Python environment and package management _inside the container_. uv handles:
- Virtual environment creation and management (replaces venv/pyenv)
- Package installation and dependency resolution (replaces pip)
- Project dependency management via `pyproject.toml`

**Important**: When running Python code, prefix commands with `uv run` to maintain the proper environment:

```bash
# Example: Running the pipeline
uv run python src/housing/scripts/pipeline_example.py

# Example: Running tests
uv run pytest tests/

# Example: Running a notebook (in devcontainer)
# Just open the notebook file and run cells directly
```

### Container Volume Structure

```
Container: /project/
├── src/           # Your source code (mounted from host repo)
│   └── housing/   # Python package with your code
│       ├── scripts/  # Executable scripts
│       └── *.py      # Importable modules
├── data/          # Data directory (mounted from HOST_DATA_DIR)
├── notebooks/     # Jupyter notebooks
├── tests/         # Test files
├── .venv/         # Python virtual environment (created in container)
├── pyproject.toml # Project configuration
└── ...
```


## Usage & Testing

### Working with the Housing Package

The project uses a Python package called `housing` located in `src/housing/`. The package is organized as follows:

```
src/housing/
├── __init__.py                    # Package initialization
├── preprocess_util_lib_example.py # Importable utility functions
└── scripts/                       # Executable scripts
    ├── __init__.py
    └── pipeline_example.py        # Example pipeline script
```

**Importable Code**: Use functions and classes from the main package:
```python
# In notebooks or Python scripts
from src.housing.preprocess_util_lib_example import generate_random_dataframe

# Use the function
df = generate_random_dataframe(rows=100)
```

**Executable Scripts**: Run scripts from the scripts directory:
```bash
# Run pipeline scripts
uv run python src/housing/scripts/pipeline_example.py
```

### Data Management

- Set `DATA_DIR` in your `.env` file to specify where data lives on your host
- This directory is mounted to `/project/data` inside the container
- Keep data separate from code to avoid repository bloat and enable easy data sharing

### Testing Your Setup

Run the command `make test-pipeline`. If your setup is working you should see a file `sample_output.csv` appear in your data directory. 


### Docker & Make Commands

We use `docker` and `make` to run our code. Available `make` commands:

* `make help`: Show all available commands and descriptions
* `make build-only`: Build the Docker image only (useful for testing Dockerfile changes)
* `make devcontainer`: Build and prepare devcontainer for VS Code/Cursor
* `make run-interactive`: Create a container and load an interactive bash session
* `make test`: Run all tests with pytest
* `make test-pipeline`: Run the pipeline example script
* `make clean`: Clean up Docker images and containers

**Note**: For notebook development, use the devcontainer workflow instead of command-line tools for the best experience.

The file `Makefile` contains details about the specific commands that are run when calling each `make` target.




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