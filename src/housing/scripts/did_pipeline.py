
"""DiD Analysis Pipeline.

This script implements the staggered Difference-in-Differences analysis steps:
1. Load data (Trajectories, Boundaries, STR Prohibitions)
2. Prepare panel data (Rental Time Series, Zip->Tract conversion)
3. Generate DiD indicators (Treatment timing)
4. Perform descriptive analysis (Trends, Balance, Adoption)
5. Event study regression and plot
6. Generate visualizations
"""
import logging
import os
from pathlib import Path

from pipeline import Pipeline

# Loaders
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.rental_data import RentalDataLoader

# Processors
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.processors.time_series_zip_to_tract import TimeSeriesZipToTractProcessor
from housing.components.processors.treatment_indicator import TreatmentIndicatorProcessor

# Analyzers & Visualizers
from housing.components.analyzers.did_descriptive import DIDDescriptiveAnalyzer
from housing.components.analyzers.event_study import EventStudyAnalyzer
from housing.components.visualizers.did_trends import DIDTrendsVisualizer
from housing.components.visualizers.event_study import EventStudyVisualizer

logger = logging.getLogger(__name__)

# Paths used by loaders (must match loader defaults when run in container)
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))
TRACT_SHP = DATA_ROOT / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
ZORI_CSV = DATA_ROOT / "Zip_zori_uc_sfrcondomfr_sm_month.csv"

DID_PREFLIGHT_MSG = (
    "If data files exist but you see 'Resource deadlock avoided' (Errno 35) or "
    "GDAL shapefile errors, the project may be on a cloud-synced folder (e.g. Box). "
    "Copy the data folder to a local directory and run:\n"
    "  cp -r data /tmp/chicago_data\n"
    "  DATA_DIR=/tmp/chicago_data make run-did-pipeline"
)


def _preflight_check() -> None:
    """Verify required data files exist and are readable before running the pipeline."""
    missing = []
    if not TRACT_SHP.exists():
        missing.append(str(TRACT_SHP))
    elif TRACT_SHP.stat().st_size == 0:
        logger.warning("Tract shapefile is empty (0 bytes). %s", DID_PREFLIGHT_MSG)
    if not ZORI_CSV.exists():
        missing.append(str(ZORI_CSV))
    elif ZORI_CSV.stat().st_size == 0:
        logger.warning("ZORI CSV is empty (0 bytes). %s", DID_PREFLIGHT_MSG)
    if missing:
        raise FileNotFoundError(
            "DiD pipeline requires the following data files:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload tract boundaries and ZORI (see README). "
            + DID_PREFLIGHT_MSG
        )
    # Try a quick read to catch Errno 35 (resource deadlock) on synced drives
    try:
        with ZORI_CSV.open("rb") as f:
            f.read(1)
    except OSError as e:
        if e.errno == 35:  # Resource deadlock avoided (e.g. Box + Docker)
            raise RuntimeError(
                "Could not read data file (Errno 35). "
                "This often happens when the project is on a cloud-synced folder.\n"
                + DID_PREFLIGHT_MSG
            ) from e
        raise
    logger.info("Preflight OK: tract shapefile and ZORI CSV found")


def run_did_analysis() -> tuple:
    """Run the complete DiD analysis pipeline."""
    logger.info("Starting DiD Analysis Pipeline")
    _preflight_check()

    pipeline = Pipeline("Chicago Housing DiD Analysis")
    
    # 1. Load Data
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    # Load snapshot rental data for crosswalk generation
    pipeline.register_component(RentalDataLoader()) 
    # Load time series rental data for analysis
    pipeline.register_component(TimeSeriesRentalLoader())
    
    # 2. Process Data
    # Generate Zip-to-Tract crosswalk
    pipeline.register_component(ZipToTractProcessor())
    
    # Convert panel data to tract level
    pipeline.register_component(TimeSeriesZipToTractProcessor())
    
    # Add treatment indicators (creates the final DiD panel)
    pipeline.register_component(TreatmentIndicatorProcessor())
    
    # 3. Analyze & Visualize
    pipeline.register_component(DIDDescriptiveAnalyzer())
    pipeline.register_component(DIDTrendsVisualizer())
    pipeline.register_component(EventStudyAnalyzer())
    pipeline.register_component(EventStudyVisualizer())

    # Execute
    results = pipeline.execute()
    
    logger.info("DiD Analysis Pipeline Completed Successfully")
    return pipeline, results


if __name__ == "__main__":
    run_did_analysis()
