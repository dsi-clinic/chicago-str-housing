## Summary

**Robustness:** trend matching currently uses **`k_neighbors=3`** ([`TrendMatchingProcessor`](src/housing/components/processors/trend_matching.py), registered in [`did_pipeline_callaway_santanna.py`](src/housing/scripts/did_pipeline_callaway_santanna.py)). Run **k = 1 … 5** (or 1–5 as agreed) and report how **main CS / TWFE findings** and **matching diagnostics** move.

## Motivation

Control pool size and reuse change with k; the paper should show sensitivity of headline estimates to this design knob, not only the default.

## Implementation ideas

- Add optional env e.g. `DID_MATCH_K_NEIGHBORS` (integer) read when constructing `TrendMatchingProcessor`, **or** a small shell/Make loop over k writing to `output/did-cs-robustness-k{k}/` (or whitepaper suffix).
- Reuse existing exports: `did_matching_diagnostics.csv`, `did_matching_control_reuse.csv`, `did_story_matching_love.png`.
- Summarize in an appendix table: k, n matched tracts, max control reuse, pooled ATT (CS + optional CS w/ controls).

## Acceptance criteria

- [ ] At least five runs (k∈{1,2,3,4,5}) documented with output paths or a single CSV summary committed under `docs/` (not raw `output/` in git).
- [ ] Paper/deck: one robustness panel or table referencing the sweep.
- [ ] Note any k where pipeline fails or cohorts drop below `min_cohort_size`.

## References

- [`docs/methodology-audit/matching_refactor.md`](docs/methodology-audit/matching_refactor.md)
