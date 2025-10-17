"""Shared constants for housing analysis components."""

# ============================================================================
# CORRELATION ANALYSIS THRESHOLDS
# ============================================================================

# Correlation strength thresholds for classification
CORRELATION_NEGLIGIBLE_THRESHOLD = 0.1
CORRELATION_WEAK_THRESHOLD = 0.3
CORRELATION_MODERATE_THRESHOLD = 0.5
CORRELATION_STRONG_THRESHOLD = 0.7

# Statistical thresholds (aliases for backwards compatibility)
STRONG_CORRELATION_THRESHOLD = 0.7
MODERATE_CORRELATION_THRESHOLD = 0.5

# CRS for geographic data (WGS 84)
GEOGRAPHIC_CRS = "EPSG:4326"
