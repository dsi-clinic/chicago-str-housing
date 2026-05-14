# Crosswalk Refactor

## Why this changed

The original ZIP-to-tract interpolation used intersection areas normalized
*within ZIP codes*. That is mechanically valid as a ZIP-side decomposition, but
it is not the natural weighting scheme for a tract-level outcome.

For tract-month rents, the more defensible quantity is:

- how much of tract `i` lies in ZIP `z`, not
- how much of ZIP `z` lies in tract `i`.

The original processor also computed areas in `EPSG:4326`, where polygon areas
are in degree units rather than projected linear units.

## What changed

`ZipTractCrosswalkProcessor` now:

1. Reprojects ZIP and tract geometries to `EPSG:3435` before area calculation.
2. Computes and stores both:
   - `zip_area_share`
   - `tract_area_share`
3. Computes tract coverage diagnostics:
   - `tract_coverage_share`
   - `n_overlapping_zips`

`TimeSeriesZipToTractProcessor` now defaults to `tract_area_share` as the
interpolation weight.

## Why this is better

Using tract-oriented weights aligns the interpolation with the target estimand:
tract-level rents. It avoids overweighting ZIP fragments simply because they
sit inside a large ZIP polygon.

Projected areas make the geometry calculations interpretable and stable.

## What to inspect after each run

- `did_crosswalk_diagnostics.csv`
- `did_crosswalk_tract_coverage.csv`
- `did_descriptive_sample_lineage.csv`

Key questions:

1. How many tracts are covered by the Chicago ZIP system at all?
2. How many tracts have near-complete coverage?
3. Are there low-coverage tracts that should be excluded in a sensitivity run?

## Remaining limitation

The tract panel still depends on ZIP-level ZORI. That means the tract outcome is
an interpolation, not a direct tract rent measure. The refactor improves the
mapping logic, but it does not eliminate the measurement-error problem inherent
in ZIP-to-tract allocation.
