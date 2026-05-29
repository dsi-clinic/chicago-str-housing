# Methodology Audit Notes

This folder captures refactors and open risks in the tract-level DiD design so
future runs do not rely on oral history or agent memory.

Files:

- `crosswalk_refactor.md` — why ZIP-to-tract interpolation was changed to use
  projected, tract-oriented area shares and what diagnostics to inspect.
- `matching_refactor.md` — why the trend-matching design was tightened, what it
  now matches on, and what limitations still remain.

Related runtime artefacts written by the pipeline:

- `did_crosswalk_diagnostics.csv`
- `did_crosswalk_tract_coverage.csv`
- `did_matching_diagnostics.csv`
- `did_matching_control_reuse.csv`
- `did_descriptive_sample_lineage.csv`

**Story / deck graphics** (written by `DIDStoryTablesAnalyzer` + `DIDStoryGraphicsVisualizer` after descriptives):

- `did_story_matching_balance_long.csv`, `did_story_covariate_smd_pre.csv`, `did_story_treatment_tract_profile.csv`
- `did_story_sample_lineage.png` — horizontal tract funnel by construction stage
- `did_story_pre_trends_scatter.png` — pre-period slope vs level (matching features)
- `did_story_matching_love.png` — standardized mean differences before vs after matching
- `did_story_control_reuse.png` — histogram of how often each control tract is reused
- `did_story_cumulative_adoption.png` — cumulative treated-tract adoption
- `did_story_pre_rent_violin.png` — pre-treatment rent by ever-treated status

The white-paper deck can stay concise. These notes are the longer-form context
for why the sample construction changed and how to defend it.
