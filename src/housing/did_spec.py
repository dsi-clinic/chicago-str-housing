"""Single source of truth for Chicago STR DiD pipeline defaults.

Pipelines under ``housing/scripts/did_pipeline*.py`` should import from here so
treatment rules, trend matching, CS options, paths, and TWFE windows stay aligned.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Final

# --- Paths (honor DATA_DIR / DID_CS_OUTPUT_DIR at call time) ---


def default_data_root() -> Path:
    """Return ``DATA_DIR`` (or default ``/project/data``) as a :class:`~pathlib.Path`."""
    return Path(os.environ.get("DATA_DIR", "/project/data"))


def tract_shapefile_path() -> Path:
    """Cook County tract TIGER shapefile under :func:`default_data_root`."""
    return default_data_root() / "tl_2023_17_tract" / "tl_2023_17_tract.shp"


def zori_csv_path() -> Path:
    """ZORI zip-level rent CSV under :func:`default_data_root`."""
    return default_data_root() / "Zip_zori_uc_sfrcondomfr_sm_month.csv"


def listings_csv_path() -> Path:
    """Airbnb listings CSV under :func:`default_data_root`."""
    return default_data_root() / "listings.csv"


def did_cs_output_dir() -> str:
    """Return ``DID_CS_OUTPUT_DIR`` or default ``/project/output/did-cs``."""
    return os.environ.get("DID_CS_OUTPUT_DIR", "/project/output/did-cs")


# --- STR prohibition → tract (shared across DiD pipelines) ---

DID_STR_PROHIBITION_POINTS_ID_COLUMN: Final = "application_id"
DID_STR_PROHIBITION_POINTS_AGGREGATE_COLUMNS: Final[dict[str, Any]] = {
    "prohibition_date": "min",
    "number_of_units": "sum",
}

# --- Treatment threshold (year-specific share gate) ---

DID_TREATMENT_THRESHOLD_PERCENTILE: Final = 0.25

# --- Trend matching (matched panel for parallel trends) ---

DID_TREND_MATCH_K_NEIGHBORS: Final = 3
DID_TREND_MATCH_MIN_PRE_PERIODS: Final = 6
DID_TREND_MATCH_CALIPER: Final[float | None] = None

# Two-feature (slope + level): reproduces published DSI clinic baseline matching.
DID_TREND_MATCH_FEATURES_2: Final[tuple[str, ...]] = (
    "pre_trend_slope",
    "avg_pre_rent",
)

# Five-feature (slope + level + lagged levels): stricter trajectory matching.
DID_TREND_MATCH_FEATURES_5: Final[tuple[str, ...]] = (
    "pre_trend_slope",
    "avg_pre_rent",
    "rent_lag_1",
    "rent_lag_6",
    "rent_lag_12",
)


def resolve_trend_match_k_neighbors() -> int:
    """Return ``DID_MATCH_K_NEIGHBORS`` env override or :data:`DID_TREND_MATCH_K_NEIGHBORS`."""
    raw = os.environ.get("DID_MATCH_K_NEIGHBORS")
    if raw is not None and raw.strip():
        return int(raw)
    return DID_TREND_MATCH_K_NEIGHBORS


def resolve_trend_match_features() -> tuple[str, ...]:
    """Return matching feature tuple from ``DID_MATCH_FEATURES`` env override.

    Accepted values:
    - ``slope_level``, ``2``, ``2feat``: slope + average pre-rent (boss baseline)
    - ``slope_level_lags``, ``5``, ``5feat`` (default): adds three lagged rent levels
    """
    raw = os.environ.get("DID_MATCH_FEATURES", "slope_level_lags").strip().lower()
    if raw in {"slope_level", "2", "2feat", "two", "boss"}:
        return DID_TREND_MATCH_FEATURES_2
    if raw in {"slope_level_lags", "5", "5feat", "five", "strict"}:
        return DID_TREND_MATCH_FEATURES_5
    msg = (
        "DID_MATCH_FEATURES must be 'slope_level' (2-feature) or "
        f"'slope_level_lags' (5-feature); got {raw!r}"
    )
    raise ValueError(msg)


def resolve_trend_match_caliper() -> float | None:
    """Return ``DID_MATCH_CALIPER`` env override or :data:`DID_TREND_MATCH_CALIPER`.

    Set ``DID_MATCH_CALIPER=2.0`` (for example) to reject matches with standardised
    Euclidean distance > 2.0.  Unset or empty keeps the default of no caliper.
    """
    raw = os.environ.get("DID_MATCH_CALIPER")
    if raw is not None and raw.strip():
        return float(raw)
    return DID_TREND_MATCH_CALIPER


def resolve_treatment_threshold_percentile() -> float:
    """Return ``DID_THRESHOLD_PERCENTILE`` env override or default percentile."""
    raw = os.environ.get("DID_THRESHOLD_PERCENTILE")
    if raw is not None and raw.strip():
        return float(raw)
    return DID_TREATMENT_THRESHOLD_PERCENTILE


# --- Callaway–Sant'Anna: baseline stack (main CS, heterogeneity, spillover) ---

DID_CS_COMPARISON_GROUP: Final = "nevertreated"
DID_CS_ANTICIPATION: Final = 0
DID_CS_MIN_COHORT_SIZE: Final = 5

# --- Callaway–Sant'Anna: covariate-adjusted pipeline (more comparisons) ---

DID_CS_COMPARISON_GROUP_WITH_CONTROLS: Final = "notyettreated"

# --- TWFE event study window ---

DID_TWFE_PRE_PERIODS: Final = 12
DID_TWFE_POST_PERIODS: Final = 36

# --- Heterogeneity: Airbnb tract density winsorization ---

DID_AIRBNB_DENSITY_WINSOR_PERCENTILE: Final = 0.99

# --- CS post-treatment trajectory phases (months since treatment, inclusive) ---

DID_CS_TRAJECTORY_PHASE_BOUNDARIES: Final[tuple[tuple[int, int], ...]] = (
    (0, 12),
    (13, 24),
    (25, 36),
)
DID_CS_TRAJECTORY_PHASE_LABELS: Final[tuple[str, ...]] = ("early", "mid", "late")
