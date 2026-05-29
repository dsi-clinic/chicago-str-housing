#!/usr/bin/env python3
"""Re-plot seasonality cohort comparison from saved cohort-dynamics CSVs (no CS re-fit)."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from housing.scripts.run_seasonality_diagnostic import _plot_cohort_comparison

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    """CLI entrypoint: replot seasonality cohort comparison from saved CSVs."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-csv",
        type=Path,
        default=REPO_ROOT
        / "docs"
        / "robustness"
        / "tables"
        / "seasonality_raw_cohort_dynamics.csv",
    )
    parser.add_argument(
        "--demean-csv",
        type=Path,
        default=REPO_ROOT
        / "docs"
        / "robustness"
        / "tables"
        / "seasonality_demean_cohort_dynamics.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT
        / "docs"
        / "robustness"
        / "figures"
        / "did_cohort_dynamics_seasonality_compare.png",
    )
    args = parser.parse_args()
    if not args.raw_csv.exists() or not args.demean_csv.exists():
        raise SystemExit(
            "Missing saved dynamics CSVs. Run seasonality diagnostic once, or export "
            "cs_cohort_dynamics from raw/demean branches to docs/robustness/tables/."
        )
    raw = pd.read_csv(args.raw_csv)
    dem = pd.read_csv(args.demean_csv)
    _plot_cohort_comparison(raw, dem, args.out)
    logger.info("Wrote paginated seasonality figures under %s", args.out.parent)


if __name__ == "__main__":
    main()
