#!/usr/bin/env python3
"""Regenerate selected white-paper figures from saved pipeline outputs (no full DiD run)."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

os.environ.setdefault("USE_PYGEOS", "0")
os.environ.setdefault("MPLBACKEND", "Agg")

import geopandas as gpd
import pandas as pd

from housing.components.visualizers.callaway_santanna import (
    plot_paginated_cohort_panels,
)
from housing.components.visualizers.did_sample_map import (
    _prepare_sample_geometries,
    _save_stacked_maps,
)

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
PLOT_PRE_MONTHS = 12
PLOT_POST_MONTHS = 36


def _regenerate_maps(
    tract_table: Path,
    tract_shp: Path,
    city_shp: Path | None,
    out_dir: Path,
) -> None:
    tract_df = pd.read_csv(tract_table)
    boundaries = gpd.read_file(tract_shp)
    city = gpd.read_file(city_shp) if city_shp and city_shp.exists() else None
    gdf, bounds = _prepare_sample_geometries(tract_df, boundaries, city, logger=logger)
    out_dir.mkdir(parents=True, exist_ok=True)
    _save_stacked_maps(
        gdf,
        bounds,
        out_dir / "did_spatial_sample.png",
        suptitle="DiD matched sample: treatment status and timing",
    )

    logger.info("Maps written to %s", out_dir)


def _regenerate_cohort_dynamics(cohort_csv: Path, out_dir: Path) -> None:
    cohort_df = pd.read_csv(cohort_csv)
    plot_df = cohort_df[
        (cohort_df["rel_time"] >= -PLOT_PRE_MONTHS)
        & (cohort_df["rel_time"] <= PLOT_POST_MONTHS)
    ]
    plot_paginated_cohort_panels(
        plot_df,
        out_dir,
        "did_cohort_dynamics",
        suptitle="Cohort-specific dynamic treatment effects (matched CS)",
        logger=logger,
    )
    p1 = out_dir / "did_cohort_dynamics_p1.png"
    legacy = out_dir / "did_cohort_dynamics.png"
    if p1.exists():
        legacy.write_bytes(p1.read_bytes())


def main() -> None:
    """CLI entrypoint: regenerate sample maps and paginated cohort figures."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Regenerate white-paper figures from artefacts"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "output" / "did-cs-whitepaper-2feat-threshold",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("DATA_DIR", REPO_ROOT / "data")),
    )
    parser.add_argument("--maps-only", action="store_true")
    parser.add_argument("--cohorts-only", action="store_true")
    args = parser.parse_args()

    out = args.output_dir
    data = args.data_dir
    tract_shp = data / "tl_2023_17_tract" / "tl_2023_17_tract.shp"
    city_shp = data / "chicago_boundaries" / "chicago_boundaries.shp"
    if not city_shp.exists():
        city_shp = (
            data
            / "Boundaries_-_Community_Areas_2022"
            / "Boundaries_-_Community_Areas_2022.shp"
        )

    do_all = not args.maps_only and not args.cohorts_only
    if args.maps_only or do_all:
        table = out / "did_spatial_sample_tract_table.csv"
        if table.exists() and tract_shp.exists():
            _regenerate_maps(
                table, tract_shp, city_shp if city_shp.exists() else None, out
            )
        else:
            logger.warning("Missing %s or shapefile; cannot regenerate maps.", table)

    if args.cohorts_only or do_all:
        cohort_csv = out / "did_cs_cohort_dynamics.csv"
        if cohort_csv.exists():
            _regenerate_cohort_dynamics(cohort_csv, out)
        else:
            logger.warning("Missing %s", cohort_csv)


if __name__ == "__main__":
    main()
