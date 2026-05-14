"""
Join clustering_data.geojson with treatment profile CSVs to produce
tracts_treatment.geojson for the interactive dashboard maps.

Adds per-tract centroid coordinates and STR prohibition unit counts
so the dashboard can overlay a prohibition-intensity circle layer.

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
from shapely.geometry import shape

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
        tid   = str(feat["properties"].get("tract_id", ""))
        info  = profile_map.get(tid, {})
        props = feat["properties"]

        # Centroid for the circle-marker overlay
        geom     = shape(feat["geometry"])
        centroid = geom.centroid

        features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": {
                "tract_id":         tid,
                "ever_treated":     int(info["ever_treated"]) if "ever_treated" in info else -1,
                "role":             info.get("role", "not_in_sample"),
                # Prohibition intensity for the overlay layer
                "prohibition_units": int(props.get("str_prohibition_units_total") or 0),
                "prohibition_density": float(props.get("str_prohibition_building_density") or 0.0),
                # Centroid (WGS-84) for positioning circle markers
                "centroid_lng": round(centroid.x, 6),
                "centroid_lat": round(centroid.y, 6),
            },
        })

    out = {"type": "FeatureCollection", "features": features}
    with open(out_path, "w") as f:
        json.dump(out, f)

    in_sample = sum(1 for f in features if f["properties"]["role"] != "not_in_sample")
    treated   = sum(1 for f in features if f["properties"]["ever_treated"] == 1)
    with_proh = sum(1 for f in features if f["properties"]["prohibition_units"] > 0)
    print(
        f"✓ {mode}: {out_path.name}  "
        f"({len(features)} tracts, {in_sample} in sample, "
        f"{treated} ever-treated, {with_proh} with prohibitions)"
    )


if __name__ == "__main__":
    generate("binary")
    generate("threshold")
