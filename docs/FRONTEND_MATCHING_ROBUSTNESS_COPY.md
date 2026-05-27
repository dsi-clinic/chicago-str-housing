# Frontend Matching Robustness Copy

Updated: 2026-05-14

This note condenses the matching-robustness story into short modules that can be reused in the frontend, slide captions, or scrollytelling sections.

Use the order below:

1. Sample funnel
2. Full panel versus matched sample
3. Matching balance
4. Residualized robustness

## Card 1: The Sample Narrows Before Estimation

**Headline**

The rent analysis does not start with every Chicago tract.

**Body copy**

The tract rent panel is built in stages. The biggest contractions happen before matching: first from all Chicago tracts to tracts touched by the Chicago ZIP system, then from those tracts to the ones observed in the ZORI rent panel.

**Key numbers**

- Chicago tract boundaries: `1,332`
- ZIP-tract crosswalk coverage: `867`
- Rent panel coverage: `842`
- ACS coverage within rent panel: `829`

**Figure pairing**

- Threshold: [did_story_sample_lineage.png](../output/did-cs-whitepaper-threshold/did_story_sample_lineage.png)
- Binary: [did_story_sample_lineage.png](../output/did-cs-whitepaper-binary/did_story_sample_lineage.png)

**Short caption**

"Most sample loss happens before matching. The main constraints are ZIP-to-tract coverage and rent-panel availability, not ACS alone."

## Card 2: Matching Makes the Comparison Group Tighter

**Headline**

Matching reduces the estimated effect, but does not erase it.

**Body copy**

The primary design uses the full tract-month panel and a heterogeneity-robust Callaway-Sant'Anna estimator. Matching then reruns the analysis on a narrower set of treated tracts and their closest untreated comparisons. That restriction lowers the estimated effect size, which shows the result is sensitive to how the comparison group is constructed.

**Key numbers**

Threshold:

- Full-panel CS ATT: `55.97`
- Matched-sample CS ATT: `14.74`

Binary:

- Full-panel CS ATT: `48.79`
- Matched-sample CS ATT: `26.06`

**Figure pairing**

- Threshold full panel: [did_callaway_santanna_event_study_full_panel.png](../output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study_full_panel.png)
- Threshold matched: [did_callaway_santanna_event_study.png](../output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study.png)
- Binary full panel: [did_callaway_santanna_event_study_full_panel.png](../output/did-cs-whitepaper-binary/did_callaway_santanna_event_study_full_panel.png)
- Binary matched: [did_callaway_santanna_event_study.png](../output/did-cs-whitepaper-binary/did_callaway_santanna_event_study.png)

**Short caption**

"Matching makes treated and untreated tracts more comparable in pre-treatment rent space, but it also changes the size of the estimate."

## Card 3: Matching Improves Balance Only Partially

**Headline**

The matched sample is still not cleanly balanced.

**Body copy**

The refactored matching step improves comparability on pre-treatment slope and rent level, but substantial imbalance remains. That means matching is useful as a robustness check, not strong enough to carry the identification argument on its own.

**Key numbers**

Threshold:

- Slope SMD: `1.357 -> 0.727`
- Pre-rent SMD: `0.683 -> 0.574`
- Max control reuse: `30`

Binary:

- Slope SMD: `1.345 -> 0.996`
- Pre-rent SMD: `0.692 -> 0.549`
- Max control reuse: `64`

**Figure pairing**

- Threshold balance: [did_story_matching_love.png](../output/did-cs-whitepaper-threshold/did_story_matching_love.png)
- Binary balance: [did_story_matching_love.png](../output/did-cs-whitepaper-binary/did_story_matching_love.png)

**Short caption**

"Matching improves balance, but not enough to claim that pre-treatment differences have been solved."

## Card 4: Residualization Improves the Pre-Period Story, But Does Not Resolve It

**Headline**

The residualized event studies look better near treatment, but early pre-trends remain.

**Body copy**

After removing ACS covariates and tract-specific linear trends, the pre-treatment path moves closer to zero near the treatment date. That is useful evidence that observable differences and local trend differences matter. But the earlier pre-treatment leads are still not flat, so the residualized design should be read as sensitivity analysis rather than a definitive correction.

**Key numbers**

Threshold:

- Residualized CS ATT: `-89.61`
- Significant pre-period coefficients: `9/11`

Binary:

- Residualized CS ATT: `-70.78`
- Significant pre-period coefficients: `7/11`

**Figure pairing**

- Threshold residualized: [did_callaway_santanna_event_study_with_controls.png](../output/did-cs-whitepaper-threshold/did_callaway_santanna_event_study_with_controls.png)
- Binary residualized: [did_callaway_santanna_event_study_with_controls.png](../output/did-cs-whitepaper-binary/did_callaway_santanna_event_study_with_controls.png)

**Short caption**

"Residualization improves local pre-treatment alignment, but it does not produce a fully flat pre-period."

## Recommended Frontend Framing

Use these points consistently:

- The full-panel CS estimate is the main result.
- Threshold and binary treatment definitions show treatment-classification sensitivity.
- Matching is a robustness restriction on the comparison group.
- Residualization is a robustness check on observable differences and local trend structure.
- The paper should discuss parallel trends as a sensitivity issue, not as a simple visual pass/fail.

## One-Paragraph Version

"Our main estimate uses the full tract-month panel and a Callaway-Sant'Anna staggered DiD design. We then test how sensitive that result is to two stricter choices: first, restricting the comparison group through pre-treatment matching, and second, residualizing rents using ACS covariates and tract-specific linear trends. Matching reduces the estimated effect but does not eliminate it, while residualization improves the pre-period pattern near treatment without fully removing earlier pre-trend differences. Taken together, these checks strengthen the interpretation of the full-panel estimate as the primary result while making clear that identification remains sensitive to comparison-group construction and trend adjustment."
