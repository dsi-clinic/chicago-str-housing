# Chicago STR prohibition context — reading notes

- **Administrative prohibition records** under the Shared Housing Ordinance assign buildings timestamps and coordinates at signing; aggregated to tract-month treatment indicators in [`tract_prohibition_dates.py`](../../src/housing/components/processors/tract_prohibition_dates.py).

- **Economic rationale:** policymakers curtail nightly-rent inventory where it competes with long-term housing supply; renters’ outcomes may respond through rents, eviction risk, or capital maintenance—see substantive papers you add locally to PDF + `literature/references.bib`.

- **This project’s outcome** uses ZIP-month **Zillow Observed Rent Index** mapped to Census tracts with the HUD-style crosswalk emitted by [`zip_tract_crosswalk.py`](../../src/housing/components/processors/zip_tract_crosswalk.py).

- Tie narrative to **spatial concentration** (`did_spatial_sample*.png`) and **adoption / parallel trend** panels (`did_adoption_curve.png`, `did_parallel_trends.png`) produced by [`DiDSampleMapVisualizer`](../../src/housing/components/visualizers/did_sample_map.py) and [`DIDTrendsVisualizer`](../../src/housing/components/visualizers/did_trends.py); pair with **`pretrend_*.csv`** summaries for methodological transparency.
