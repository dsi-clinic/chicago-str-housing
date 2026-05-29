r"""Prototype helpers for narrower synthetic-control / Synth-DiD workflows.

Loads the tract-month panel emitted by TreatmentIndicatorProcessor and summarizes
counts for choosing a focal cohort ``g`` before invoking external Synth/SynthDiD libraries.

Primary staggered estimator remains ``CallawaySantAnnaAnalyzer`` /
``CallawaySantAnnaWithControlsAnalyzer`` via ``did_pipeline_callaway_santanna``.

See ``docs/exploratory/SYNTHETIC_PROTOTYPE_NOTES.md``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd


def summarize_cohorts(csv_path: Path) -> pd.DataFrame:
    """Return counts of tracts keyed by earliest treated month."""
    panel = pd.read_csv(csv_path, parse_dates=["month", "first_prohibition_date"])
    first_treat = (
        panel.loc[panel["treated"].eq(1), ["tract_geoid", "month"]]
        .groupby("tract_geoid")["month"]
        .min()
    )
    return first_treat.groupby(first_treat).size().sort_index()


def main() -> None:
    """CLI entrypoint: print cohort-size table for exploratory synthetic designs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--panel_csv",
        type=Path,
        default=Path(
            os.environ.get("DID_PANEL_CSV", "output/did-cs/did_panel_data.csv")
        ),
        help="Tract-month panel CSV from the DiD pipeline (default: DID_PANEL_CSV or output/).",
    )
    args = parser.parse_args()

    cohort_counts = summarize_cohorts(args.panel_csv)
    print("Tracts-by-first-treated-month:")
    print(cohort_counts.to_string())


if __name__ == "__main__":
    main()
