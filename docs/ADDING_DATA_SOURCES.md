# Adding New Data Sources

The pipeline is designed to be **fully extensible** - you can add new data sources without modifying any Python code!

## How It Works

The pipeline automatically discovers all data paths from your YAML configuration file. Any field ending with `_path` in the `data:` section will be:

1. ✅ Automatically validated (URLs are allowed, local paths are checked for existence)
2. ✅ Added to the pipeline context as `data_paths`
3. ✅ Available to all components in your pipeline

## Adding a New Data Source

### Step 1: Update Your YAML Config

Edit `config/pipeline_config.yaml` and add your new data path:

```yaml
data:
  # Existing data sources
  rental_data_path: /project/data/Zip_zori_uc_sfrcondomfr_sm_month.csv
  zip_boundaries_path: https://data.cityofchicago.org/resource/unjd-c2ca.json
  community_boundaries_path: https://data.cityofchicago.org/resource/igwz-8jzy.json
  tract_boundaries_path: /project/data/tl_2023_17_tract/tl_2023_17_tract.shp
  
  # NEW: Your custom data sources (just add them here!)
  airbnb_data_path: /project/data/listings.csv
  str_prohibition_data_path: /project/data/str_prohibitions.json
```

### Step 2: Access in Your Component

That's it! Your new data paths are now available in the pipeline context:

```python
from pipeline.base import Loader

class AirbnbDataLoader(Loader):
    def __init__(self):
        super().__init__("airbnb_data_loader", "Load Airbnb listings data")
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        # The path is automatically available!
        airbnb_path = context["data_paths"]["airbnb_data"]
        
        df = pd.read_csv(airbnb_path)
        return {"airbnb_data": df}
```

## Path Naming Convention

- **Field name in YAML**: Must end with `_path` (e.g., `airbnb_data_path`)
- **Key in context**: The `_path` suffix is removed (e.g., `airbnb_data`)

## Supported Path Types

### Local Files
```yaml
my_data_path: /project/data/myfile.csv
my_data_path: ./relative/path/data.json
```

### URLs (Web APIs)
```yaml
chicago_api_path: https://data.cityofchicago.org/resource/endpoint.json
external_data_path: http://example.com/data.csv
```

## Example: Complete Workflow

```yaml
# config/pipeline_config.yaml
data:
  # Census data
  tract_boundaries_path: /project/data/census/tracts.shp
  
  # Airbnb data
  airbnb_listings_path: /project/data/airbnb/listings.csv
  airbnb_reviews_path: /project/data/airbnb/reviews.csv
  
  # City regulations
  str_prohibition_zones_path: https://data.cityofchicago.org/resource/str-zones.json
  
  # Crime data
  crime_incidents_path: https://data.cityofchicago.org/resource/crimes.json
```

All of these will be automatically discovered and available as:
- `context["data_paths"]["tract_boundaries"]`
- `context["data_paths"]["airbnb_listings"]`
- `context["data_paths"]["airbnb_reviews"]`
- `context["data_paths"]["str_prohibition_zones"]`
- `context["data_paths"]["crime_incidents"]`

## No Python Code Changes Required! 

The pipeline uses **dynamic field discovery** to find all `*_path` fields in your config. This means:

✅ You never need to edit `src/pipeline/config.py`  
✅ You never need to edit `src/pipeline/base.py`  
✅ Just add your paths to the YAML and start using them!

## Debugging

To see all available data paths, run:

```python
from pipeline import Pipeline
from pipeline.config import PipelineConfig

config = PipelineConfig()
pipeline = Pipeline("My Pipeline", config=config)
pipeline.load_config("config/pipeline_config.yaml")

# Show all discovered paths
print("Available data paths:")
for key, path in pipeline.context["data_paths"].items():
    print(f"  {key}: {path}")
```

