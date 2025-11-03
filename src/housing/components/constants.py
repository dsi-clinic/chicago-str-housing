"""Shared constants for housing analysis components."""

# ============================================================================
# CORRELATION ANALYSIS THRESHOLDS
# ============================================================================

# Correlation strength thresholds for classification
CORRELATION_NEGLIGIBLE_THRESHOLD = 0.1
CORRELATION_WEAK_THRESHOLD = 0.3
CORRELATION_MODERATE_THRESHOLD = 0.5
CORRELATION_STRONG_THRESHOLD = 0.7

# ============================================================================
# DATA PROCESSING CONSTANTS
# ============================================================================

# Minimum tract area in km² (10 hectares)
MIN_TRACT_AREA_KM2 = 0.01

# Minimum land area in square meters to exclude water-only tracts
MIN_LAND_AREA_SQ_METERS = 10000

# No-data marker from GeoJSON files
NO_DATA_MARKER = -9999

# ============================================================================
# VISUALIZATION CONSTANTS
# ============================================================================

# Cap for choropleth map display (people/km²)
MAX_POPULATION_DENSITY_DISPLAY = 100000

# Number formatting thresholds
BILLION_THRESHOLD = 1e9
MILLION_THRESHOLD = 1e6
THOUSAND_THRESHOLD = 1e3
