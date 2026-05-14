# 2025-autumn-city-of-chicago-housing

## Project Summary

### Background & Motivation

The City of Chicago enforces short-term rental (STR) prohibitions under the Shared Housing Ordinance, but it remains unclear how these prohibitions relate to housing affordability, demographic trends, and socioeconomic conditions. The team worked with the City of Chicago's Department of Technology and Innovation (DTI) to better understand the distribution of STR prohibitions and relationships with other demographic and market variables. Gaining insight into these connections is a critical step towards alleviating the City of Chicago's rising housing pressures. 

### Autumn 2025: Descriptive Analysis

#### Exploratory Data Analysis (EDA)

**Key Question:** How does STR unit density correlate with housing affordability, Airbnb listings, foreclosures, and demographic data across census tracts?

The team built a pipeline to conduct a comprehensive analysis of Chicago’s housing landscape using data from the Chicago Data Portal, U.S. Census Bureau, Airbnb, Zillow, and city administrative records. The pipeline allows the users to merge datasets and perform geospatial analysis, enabling a comprehensive view of how key housing factors vary across the city and relate to one another.

**Analysis Result:** While not all the variables we explored showed high correlation with STR unit density, significant relationships exist with population density and rental prices.

**Key outputs** are identified and described in the [Analysis Outputs](#analysis-outputs) section

#### Clustering

**Key Question:** Can clustering techniques reveal distinct "neighborhood types" based on housing and socioeconomic conditions?

**Key Question:** Do neighborhoods with high STR restrictions differ systematically from those without restrictions in terms of affordability and foreclosure activity?

**Features Used for Clustering:**
- **Census Data:** `census_median_income`, `census_median_age`, `census_pct_bachelor`, `census_median_house_value`, `census_pct_rented`
- **Zillow Data:** `rental_price_mean`
- **Airbnb Data:** `airbnb_price_mean`, `airbnb_density`
- **STR Prohibition Data:** `str_prohibition_building_density`, `str_prohibition_unit_density`
- **Affordable Housing Development Data:** `affordable_development_density`, `affordable_development_unit_density`
- **Foreclosure Data:** `foreclosure_density`

**Clustering Algorithms Tested:**
Using an elbow plot, we identified six clusters as the best number to build distinct neighborhood types.

The algorithms we tried included two traditional clustering algorithms (KMeans and Ward) and two regionalization clustering algorithms (Ward-KNN and Ward-Queens). Geodemographic clusters consider only the tabular data, so the clusters formed are naive to spatial relationships. We can use the choropleth maps and other outputs to interpret the spatial story told by these clusters. Regionalization algorithms enforce the spatial constraint that (in our case) tracts in the same cluster must be contiguous.

Enforcing the regionalization constraint greatly reduced the performance and interpretability of the resulting clusters, so we chose traditional clustering. Between the traditional clustering algorithms, KMeans performed the best, so we used it for our analysis.

*Analysis Result**:
- **First Question:** Clusters revealed neighborhood types driven by differences in STR prohibition levels and distinguished by their demographic, housing, and geographic characteristics
- **Second Question:** Because of the high separation in STR density levels between clusters, the groupings reveal that neighborhoods with higher STR restrictions differ systematically in affordability, but not in foreclosure activity.

By merging datasets and performing k-means clustering, the analysis revealed significant spatial variation across census tracts. STR distribution proved to be a non-random spatial process and the strongest distinguishing factor among 12 variables, confirming its central role in understanding housing pressures and neighborhood dynamics. 

**Key outputs** are identified and described in the [Analysis Outputs](#clustering-outputs) section.

### Winter 2026: Causal Impact Analysis

**Key Question:** What is the causal effect of STR prohibition adoption on rental prices in Chicago census tracts?

Building on the descriptive and clustering analyses, this phase implements a **staggered Difference-in-Differences (DiD) analysis** to estimate the causal impact of STR prohibitions on rental prices. Since different tracts adopted prohibitions at different times (2015-2024), we can use later-treated tracts as controls for earlier-treated ones, leveraging the variation in treatment timing to identify causal effects. The analysis uses panel data methods with two-way fixed effects (tract and time) to control for time-invariant tract characteristics and city-wide trends, and includes event study analysis to test the parallel trends assumption and examine how treatment effects evolve over time.

**Key outputs** and methodology are described in the [DiD Analysis Documentation](#did-analysis-documentation) section.

## Data

### Primary Datasets
- [Chicago's Affordable Rental Housing Developments](https://data.cityofchicago.org/Community-Economic-Development/Affordable-Rental-Housing-Developments/s6ha-ppgi/about_data): Thousands of affordable units that are supported by City of Chicago programs to maintain affordability in local neighborhoods. Includes location data, management companies, and number of units
- [House Share Prohibited Buildings List](https://data.cityofchicago.org/Buildings/House-Share-Prohibited-Buildings-List/7bzs-jsyj/about_data): A list of buildings excluded from short-term rental activity under the Shared Housing Ordinance. Includes location data, number of units, and dates.
- [Airbnb Listings](https://insideairbnb.com/get-the-data/): Short-term rental listings data including prices, locations, and property characteristics (processed and cleaned for analysis)
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



## Architecture

The codebase is contained under the `src/` directory, which is organized as follows:
```text
src/
├── housing/
│   ├── __init__.py
│   ├── components/              # “Building Blocks” of the pipeline
│   │   ├── analyzers/           # Statistical evaluation tools
│   │   ├── cluster/             # Classes + helpers for clustering pipeline
│   │   ├── loaders/             # Data loaders for each dataset
│   │   ├── processors/          # Transform + aggregate data (incl. geospatial)
│   │   ├── visualizers/         # Visualization utilities
│   │   ├── constants.py         # Shared named constants
│   │   └── utils.py             # Shared helper functions
│   │
│   └── scripts/                 # User-facing runnable scripts
│
└── pipeline/                    # Pipeline architecture + orchestration layer


```

**Generic Pipeline Framework** (`src/pipeline/`):
- Reusable, domain-agnostic framework for data analysis pipelines
- Base classes: `Pipeline`, `PipelineResult`, `PipelineComponent`, `DataLoader`, `DataProcessor`, `Analyzer`, `Visualizer`
- YAML/JSON configuration with environment variable support

**Housing Components** (`src/housing/`):
- Chicago-specific analysis components
- Reusable functions: found in `utils.py`, (e.g., formatters, metric calculators, common visualizers)
- Organized by type: loaders, processors, analyzers, visualizers
- `cluster/` sub-directory includes helper functions and classes for the clustering pipeline
-`scripts/` sub-directory includes user-facing runnable scripts for both the EDA and clustering pipelines

### Design Considerations
- **Modularity**: Each component is independently developed and testable
- **Separation of concerns**: Generic framework vs. domain-specific logic
- **Configuration-driven**: Data paths and parameters externalized
- **Logging**: Structured logging throughout for debugging and monitoring


## Quick Start

### 1. Setup Environment

Docker is required for running the analysis. Instructions on how to install Docker Desktop can be found [here](https://docs.docker.com/desktop/) 
 
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

**Required: Airbnb Data**
- Download Airbnb listings data and place in `data/listings.csv`

**Automatic: Boundary APIs**
- Community, ZIP, and city boundaries are fetched automatically from Chicago Data Portal
- Cached to `data/.cache/` on first run for faster subsequent runs
- No manual download needed!

**Required: Census API Key**
 - Request [Census API Key](https://api.census.gov/data/key_signup.html) and store it in .env  
 - Store Census API Key in `.env`

```bash
# Example: CENSUS_API_KEY = {Your-API-KEY}
```



**Automatic: City of Chicago Data Portal APIs**
- The remaining datasets are fetched automatically from Chicago Data Portal
- Cached to `data/.cache/` on first run for faster subsequent runs
- No manual download needed!

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
# Interactive development
make run-interactive

# Run the EDA pipeline
make run-eda-pipeline

# Clean up Docker artifacts
make clean
```

### 4. Run the Pipeline

```bash
# Run the housing EDA pipeline
make run-eda-pipeline

# Run the prepare data for clustering
Make run-clustering-pipeline

# Run clustering data exploration
Make run-clustering-analysis
```

The housing pipeline generates comprehensive analysis including:
- **Spatial Analysis**: Census tract-level aggregation of rental prices, STR prohibitions, and Airbnb listings
- **Correlation Analysis**: Statistical relationships between housing market indicators
- **Distribution Visualizations**: Price and density distributions across geographic areas
- **Choropleth Maps**: Spatial visualization of housing patterns clipped to Chicago boundaries

### Analysis Outputs

The pipeline generates the following visualizations in the `output/` directory:


**Rental Market Analysis:**
- `rental_distribution_analysis.png` - Rental price distributions by tract and community area
- `rental_price_maps.png` - Choropleth maps of rental prices across Chicago

**STR Prohibition Analysis:**
- `str_distribution_analysis.png` - STR units density and prohibited units distributions
- `str_density_maps.png` - Spatial maps: STR units density and STR buildings density (per km²)
- `str_correlation_analysis.png` - Correlation analysis between STR units density, rental prices, and Airbnb units density

**Airbnb Market Analysis:**
- `airbnb_distribution_analysis.png` - Airbnb price and density distributions
- `airbnb_analysis_maps.png` - Spatial maps of Airbnb pricing and density patterns

**Foreclosures Analysis:**
- `foreclosed_maps.png` - Foreclosure count choropleths by tract and community area
- `foreclosed_top10_distribution.png` - communities with ten most foreclosed buildings

### Clustering Outputs

- `clustering_data.geojson` - fully merged cleaned data containing all variables across dataset for clustering analysis
- `clustering_data_scaled.csv` - standard(scale) data on the clustering_data.geojson
- `choropleth_maps` - Grid of maps for all clustering features, using Fisher-Jenks breaks to bin the data to easily view geospatial distributions
- `scatterplot_matrix` - Grid of plots showing the distributions and pairwise correlations of features

The team selected KMeans as the main clustering output for analysis given its superior performance and interpretability, as described above. As such, the most relevant output files in the `output/clustering/` directory correspond to this algorithm:

- `kmeans_attribute_distributions.png` - KDE distribution plots for each attribute colored by cluster
- `kmeans_cluster_profiles.png` - Table of cluster centroids showing average value of each feature by cluster
- `kmeans_cluster_kruskal.png` - Kruskal-Wallis test result for each attribute across clusters
- `kmeans_cluster_pairwise_ks.png` - Pairwise Kolmogorov-Smirnov test results for each attribute
- `kmeans_cluster_pairwise_permanova.png` - Permanova test results to assess multivariate separation among clusters
- `kmeans_cluster_pairwise_manova.png` - Manova (Wilks' lambda) test results to assess multivariate centroid differences



## Development

### Creating New Components

See `docs/HOUSING_GUIDE.md` for housing component details and `docs/PIPELINE_GUIDE.md` for framework usage:
- Creating loaders, processors, analyzers, and visualizers
- Registering components in the pipeline
- Common patterns and best practices

### Configuration

The pipeline uses YAML configuration files with environment variable support. Configuration includes:
- Data file paths (can be local files or URLs)
- Analysis parameters
- Component execution order

See `docs/PIPELINE_GUIDE.md` for configuration details.

### Data Management

- Set `DATA_DIR` in your `.env` file to specify where data lives on your host
- This directory is mounted to `/project/data` inside the container
- Keep data separate from code to avoid repository bloat and enable easy data sharing
- The pipeline automatically validates data file existence 


### Make Commands

Common commands (run `make help` for full list):

* `make devcontainer` - Build devcontainer for VS Code/Cursor
* `make run-interactive` - Interactive bash session in container
* `make test` - Run all tests
* `make run-eda-pipeline` - Run housing analysis pipeline
* `make run-clustering-pipeline` - Prepare data for clustering
* `run-clustering-analysis` - Run clustering data exploration
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

- **docs/PIPELINE_GUIDE.md** - Pipeline architecture and available components
- **docs/HOUSING_GUIDE.md** - Housing components and clustering pipeline guide
- **docs/CLUSTERING_PIPELINE.md** - Clustering data preparation methodology
- **docs/CLUSTERING_ANALYSIS.md** - Clustering analysis workflow and outputs

### DiD Analysis Documentation

- **docs/str-paper/** — [README](docs/str-paper/README.md), [long-form paper](docs/str-paper/STR_PROHIBITION_PAPER.md), [policy brief](docs/str-paper/STR_POLICY_BRIEF.md); refresh archived figures + CSVs with `make sync-str-paper-figures`
- **docs/DID_STUDENT_PLAN.md** - Implementation plan for staggered DiD analysis
