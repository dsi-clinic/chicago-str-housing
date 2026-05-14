# Matching Refactor

## Why this changed

The original trend-matching step matched treated tracts to never-treated tracts
using only one scalar:

- pre-treatment rent slope

That left two problems:

1. Balance on pre-treatment rent *levels* could still be poor.
2. A one-dimensional match is hard to defend when treated tracts are visibly
   different on both growth and baseline price.

## What changed

`TrendMatchingProcessor` now matches on two pre-treatment features:

- `pre_trend_slope`
- `avg_pre_rent`

The features are standardized before nearest-neighbour matching so the distance
metric is not dominated by the larger-scale variable.

The processor now also records diagnostics:

- mean / median / tail match distance
- control reuse distribution
- standardized mean differences before and after matching

These are exported in:

- `did_matching_diagnostics.csv`
- `did_matching_control_reuse.csv`

## How to read the Love plot

The dashboard and pipeline emit a Love-style figure (`did_story_matching_love.png`) and
long-format balance rows (`did_story_matching_balance_long.csv`). Readers should not
confuse it with residualized Callaway–Sant'Anna estimates.

- **What is plotted:** For each **matching feature** (`pre_trend_slope`, `avg_pre_rent`),
  the **standardized mean difference (SMD)** between treated tracts and a comparison
  group, using the same pooled standard deviation as in `TrendMatchingProcessor`
  (`_standardized_mean_difference`).
- **Before (grey circles in the figure):** Treated vs **all** never-treated tracts that
  have enough pre-period months to enter the pre-trend module—the full pre-match
  control pool in trend space.
- **After (maroon diamonds):** Treated vs **only** the never-treated tracts that were
  actually selected as **k**-nearest neighbours on **standardized** slope and average
  pre-rent—that is the **post-refactor** matcher, not the old slope-only rule.
- **Not CS with controls:** Residualization of the outcome for doubly-robust CS is a
  separate downstream step. The Love plot summarises **design-stage** balance on
  pre-treatment summaries, not ATT magnitudes.
- **Threshold vs binary:** Two treatment definitions; the matching **machinery** is the
  same; treated sets and diagnostics differ between runs.

## Why this is better

This refactor makes the matched sample less vulnerable to the criticism that we
only aligned on a trend statistic while leaving large price-level differences in
place. Matching on slope and pre-level is still simple, but it is much easier to
explain and defend.

## What this does *not* solve

Several econometric limitations remain:

1. Matching is still nearest-neighbour matching with replacement.
2. A small set of controls can still be reused heavily.
3. There is still no hard caliper by default.
4. Matching uses summary pre-treatment features rather than full path matching.
5. It is still a design-stage restriction, so it should be presented as a
   robustness device rather than the sole identification argument.

## How to defend the design

The right defense is:

- the matching rule is pre-specified and algorithmic,
- the diagnostics are reported,
- the main CS design is still estimated transparently,
- and sensitivity to matching choices is examined rather than hidden.

The wrong defense is to claim matching fully eliminates selection concerns. It
does not. It only narrows comparators in a reproducible way.
