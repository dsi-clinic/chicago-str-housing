"""
Join clustering_data.geojson with treatment profile CSVs to produce
tracts_treatment.geojson for the interactive dashboard maps.

Usage:
  export PYTHONPATH=src
  python src/housing/scripts/generate_treatment_geojson.py

Reads:
  output/clustering_data.geojson
  output/did-cs-whitepaper-{binary,threshold}/did_story_treatment_tract_profile.csv

Writes:
  output/did-cs-whitepaper-binary/tracts_treatment.geojson
  output/did-cs-whitepaper-threshold/tracts_treatment.geojson
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

REPO_ROOT   = Path(__file__).resolve().parents[3]
GEOJSON_SRC = REPO_ROOT / "output" / "clustering_data.geojson"


def generate(mode: str) -> None:
    profile_path = REPO_ROOT / f"output/did-cs-whitepaper-{mode}/did_story_treatment_tract_profile.csv"
    out_path     = REPO_ROOT / f"output/did-cs-whitepaper-{mode}/tracts_treatment.geojson"

    profile = pd.read_csv(profile_path, dtype={"tract_geoid": str})[
        ["tract_geoid", "ever_treated", "role"]
    ]
    profile_map: dict[str, dict] = profile.set_index("tract_geoid").to_dict("index")

    with open(GEOJSON_SRC) as f:
        src = json.load(f)

    features = []
    for feat in src["features"]:
        tid = str(feat["properties"].get("tract_id", ""))
        info = profile_map.get(tid, {})
        features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": {
                "tract_id":    tid,
                "ever_treated": int(info["ever_treated"]) if "ever_treated" in info else -1,
                "role":         info.get("role", "not_in_sample"),
            },
        })

    out = {"type": "FeatureCollection", "features": features}
    with open(out_path, "w") as f:
        json.dump(out, f)

    in_sample  = sum(1 for feat in features if feat["properties"]["role"] != "not_in_sample")
    treated    = sum(1 for feat in features if feat["properties"]["ever_treated"] == 1)
    print(f"✓ {mode}: {out_path.name}  "
          f"({len(features)} tracts, {in_sample} in sample, {treated} ever-treated)")


if __name__ == "__main__":
    generate("binary")
    generate("threshold")
