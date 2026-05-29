# Synthetic-control / Synth-DID prototype (scope boundary)

Full staggered Callaway–Sant’Anna estimation on the tract-month panel stays the primary design; this note records what a tighter **synthetic** comparison could look like **without replacing** CS.

## Minimal prototype idea

Pick **one prohibition cohort \(g\) ** (e.g. tracts whose first prohibition month matches a dominant calendar spike). Define:

- Treated tract panel for months around \(g\) (narrow event window).

- Donor panel from **eligible never-treated Cook County census tracts** that pass the existing trend-match screen or a manual subset thereof.

Collapse to tract \(\times\) month or aggregated city-side series and feed into:

- Synthetic control (**Abadie–Diamond–Hainmueller** style donor weighting): one treated index vs weighted donors; placebo checks on timing.

- Synthetic difference-in-differences (**Arkhangelsky–Athey–…–Wager**) as implemented in mature packages (e.g. `synthdid` in R or community Python ports): closer to staggered pooling but **still assumptions-heavy** versus CS on the full staggered timetable.

Companion script skeleton: [`exploratory_synth_aggregate.py`](../src/housing/scripts/exploratory_synth_aggregate.py).

## Threats versus the main staggered estimator

Synthetic-style estimators sharpen **comparison-group fit** inside a narrowed sample but:

- Lose transparent aggregation over many cohort-relative windows that CS separates.

- Can overfit donor weights when donors are plentiful and outcomes noise is small.

Treat output as directional validation, not headline policy numbers, unless substantive agreement with CS emerges and identification story is tightened.
