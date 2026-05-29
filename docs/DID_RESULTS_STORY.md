# DiD Results Story

Updated: 2026-05-14

This note summarizes what the refreshed DiD pipeline is now saying after:

- refactoring the ZIP-to-tract crosswalk toward tract-oriented weights,
- improving the matching step to use pre-treatment slope plus pre-treatment rent level,
- adding a full-panel Callaway-Sant'Anna branch before matching narrows the sample.

Related methodology notes:

- [Methodology Audit Overview](methodology-audit/README.md)
- [Crosswalk Refactor](methodology-audit/crosswalk_refactor.md)
- [Matching Refactor](methodology-audit/matching_refactor.md)
- [Frontend Matching Robustness Copy](FRONTEND_MATCHING_ROBUSTNESS_COPY.md)

## Recommended presentation order

The cleanest order for the white paper and frontend is:

1. Primary design: full-panel Callaway-Sant'Anna on the tract rent panel.
2. Treatment-definition sensitivity: threshold versus binary treatment timing.
3. Matching robustness: rerun CS on the matched sample.
4. Residualized robustness: rerun CS with ACS covariates and tract-specific linear trends.

That order matches the econometric strength of the designs.

- The full-panel CS estimator is the primary estimate because it is robust to staggered timing and heterogeneous treatment effects without discarding most controls.
- Matching is best treated as a design-stage robustness check, not as the main identification argument.
- The residualized estimator is useful for checking whether observable tract differences and linear trend differences explain the baseline result, but its effect size is not directly comparable to the raw rent-level ATT.

## Core result stack

The current result stack is:

| Treatment definition | Full-panel CS ATT | Matched-sample CS ATT | Residualized CS ATT |
| --- | ---: | ---: | ---: |
| Threshold | 55.97 | 14.74 | -89.61 |
| Binary | 48.79 | 26.06 | -70.78 |

Standard errors:

| Treatment definition | Full-panel CS SE | Matched-sample CS SE | Residualized CS SE |
| --- | ---: | ---: | ---: |
| Threshold | 0.45 | 0.49 | 0.54 |
| Binary | 0.53 | 0.62 | 0.61 |

Interpretation:

- In the raw rent-level CS estimators, both treatment definitions deliver positive ATT estimates.
- Matching reduces the size of the positive ATT materially, especially under the threshold definition.
- The residualized estimator flips strongly negative in both modes, which suggests treated tracts differ substantially in observables and tract-level trend structure.
- The residualized magnitude should not be interpreted as directly comparable to the raw-rent ATT because the outcome has been residualized using pre-treatment covariates and tract-specific trends.

## What the story is saying

The best current reading is:

- The tract-rent interpolation and sample construction matter a lot. After the crosswalk fix, the baseline CS estimate is no longer near zero.
- The positive ATT survives both treatment definitions in the raw CS designs.
- The size of the effect depends on how aggressively we restrict the comparison group.
- Matching does not eliminate imbalance, so it should not be presented as if it solves the identification problem.
- The residualized negative ATT suggests that treated tracts were already on systematically different rent paths once observables and tract-specific linear trend structure are partialled out.

That means the most defensible paper story is not:

- "matching proves the effect,"

but instead:

- "the heterogeneity-robust full-panel DiD is the primary estimate, and the matched and residualized designs show how sensitive the result is to comparison-group restriction and trend adjustment."

## Treatment-definition comparison

Threshold mode keeps a narrower treatment set and a larger never-treated pool before matching:

- Threshold pre-match split: 274 treated, 568 never-treated.
- Binary pre-match split: 373 treated, 469 never-treated.

After matching:

- Threshold matched panel: 453 tracts = 274 treated + 179 controls.
- Binary matched panel: 556 tracts = 373 treated + 183 controls.

The threshold and binary estimates are directionally aligned in the raw CS designs, but the binary definition yields the larger matched-sample ATT.

This supports a frontend narrative that treatment definition changes the size of the estimated effect, but not the sign of the baseline CS result.

## Sample lineage

The descriptive funnel is now explicit:

- Chicago tract boundaries: 1,332
- ZIP-tract crosswalk coverage: 867
- Rent panel coverage: 842
- ACS coverage within rent panel: 829

So the main contraction is:

- from all Chicago tracts to those touched by the Chicago ZIP system,
- then from crosswalk tracts to those observed in the ZORI rent panel.

ACS coverage matters, but it is not the first or main source of sample loss.

Key files:

- [Default sample lineage CSV](../output/did-cs-whitepaper/did_descriptive_sample_lineage.csv)
- [Threshold sample lineage CSV](../output/did-cs-whitepaper-threshold/did_descriptive_sample_lineage.csv)
- [Binary sample lineage CSV](../output/did-cs-whitepaper-binary/did_descriptive_sample_lineage.csv)

## Matching diagnostics

Matching is better documented now, but still not strong enough to present as the central identifying design.

Threshold matching:

- slope SMD: 1.357 before, 0.727 after
- pre-rent SMD: 0.683 before, 0.574 after
- max control reuse: 30

Binary matching:

- slope SMD: 1.345 before, 0.996 after
- pre-rent SMD: 0.692 before, 0.549 after
- max control reuse: 64

So the matched sample is still materially imbalanced, especially in the binary specification.

Key files:

- [Threshold matching diagnostics](../output/did-cs-whitepaper-threshold/did_matching_diagnostics.csv)
- [Binary matching diagnostics](../output/did-cs-whitepaper-binary/did_matching_diagnostics.csv)
- [Threshold control reuse](../output/did-cs-whitepaper-threshold/did_matching_control_reuse.csv)
- [Binary control reuse](../output/did-cs-whitepaper-binary/did_matching_control_reuse.csv)

## Robustness to matching

Matching should be treated as a robustness layer with two separate questions:

1. Does restricting controls to more comparable untreated tracts materially change the estimated ATT?
2. Does the restriction materially improve the pre-treatment event-study path?

Right now the answer is:

- yes on the first question,
- only partially on the second.

That is why matching belongs in a **robustness to matching** section, not as the central research design.

Recommended robustness framing:

- Full-panel CS is the primary estimate.
- Matched-sample CS shows how the estimate changes when comparison tracts are forced to look more similar in pre-treatment rent space.
- Residualized CS shows how the estimate changes once observable ACS differences and tract-specific linear trends are partialled out.
- If all three tell the same sign story, that strengthens the paper.
- If magnitudes move a lot, that should be presented as sensitivity to design choices rather than hidden.

## Parallel trends interpretation

The current event studies should be read carefully:

- The raw full-panel and matched-sample CS event studies show sizable pre-treatment deviations.
- The residualized CS event studies look **better near treatment**, but they still do **not** produce a cleanly flat pre-period.
- So residualization improves the story, but does not eliminate the concern.

This means the project should not use event-study visuals as a simple "parallel trends passed" statement. A better statement is:

- the pre-period becomes more locally aligned after residualization,
- but meaningful early-lead deviations remain,
- so the main estimates should be accompanied by sensitivity language and robustness comparisons.

## How to improve matching further

If matching remains in the paper, the next upgrade should not just be "add more variables." The stronger path is:

1. Build features from richer pre-treatment outcome histories, not only slope plus mean.
2. Use tract-specific untreated histories where feasible, rather than one global early window.
3. Add a caliper so poor matches are excluded rather than forced.
4. Restrict matches geographically or by broad submarket when substantively justified.
5. Limit or explicitly penalize heavy control reuse.
6. Keep reporting balance and reuse diagnostics in the output tree.

Even after those upgrades, matching should still be presented as a robustness design layered on top of the full-panel CS result.

## Visual assets for the frontend

Primary figures:

- Threshold full-panel CS: [PNG](../output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study_full_panel.png)
- Threshold matched CS: [PNG](../output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study.png)
- Threshold residualized CS: [PNG](../output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study_with_controls.png)
- Binary full-panel CS: [PNG](../output/did-cs-whitepaper-binary/did_callaway_santanna_event_study_full_panel.png)
- Binary matched CS: [PNG](../output/did-cs-whitepaper-binary/did_callaway_santanna_event_study.png)
- Binary residualized CS: [PNG](../output/did-cs-whitepaper-binary/did_callaway_santanna_event_study_with_controls.png)

Supporting sample and matching figures:

- [Threshold sample lineage graphic](../output/did-cs-whitepaper-threshold/did_story_sample_lineage.png)
- [Binary sample lineage graphic](../output/did-cs-whitepaper-binary/did_story_sample_lineage.png)
- [Threshold matching balance graphic](../output/did-cs-whitepaper-threshold/did_story_matching_love.png)
- [Binary matching balance graphic](../output/did-cs-whitepaper-binary/did_story_matching_love.png)

## Suggested white-paper wording

Short version:

"Our primary specification uses the full tract-month rent panel and a Callaway-Sant'Anna staggered DiD estimator, which is robust to heterogeneous treatment timing and treatment effects. Across both treatment definitions, the baseline full-panel estimates are positive. Restricting the analysis to matched treated and control tracts reduces the size of the estimated effect but does not reverse its sign. A more demanding residualized specification that removes observed ACS differences and tract-specific linear trends yields negative residualized effects, indicating that treated tracts differ meaningfully from controls in observable characteristics and baseline trend structure. We therefore interpret the full-panel Callaway-Sant'Anna estimates as the primary results and the matched and residualized specifications as robustness checks rather than substitutes for the main design."

## What to do next

The next econometric improvement should be:

1. keep the full-panel CS design as the primary estimate,
2. add stronger formal sensitivity language around parallel trends,
3. treat matching as robustness only,
4. if matching is retained, strengthen it with calipers or richer pre-treatment outcome histories rather than relying on nearest-neighbour matching alone.

For a stronger robustness layer beyond the current matched design, a synthetic DiD style extension is a better next step than simply adding more ad hoc matching rules.
