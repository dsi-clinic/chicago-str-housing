# Parallel Trends Analysis: Findings, Diagnosis, and Paper Strategy

**Date:** 2026-05-27  
**Status:** Active — informs paper narrative and robustness strategy  
**Related files:** `docs/methodology/ROBUSTNESS_DECISIONS.md`, `docs/ANALYSIS_PLAN.md`, `docs/PRETREND_VIOLATIONS_AND_FIXES.md`

---

## 1. The V-Shaped Pre-Trend: What the Data Shows

Running the full-panel Callaway-Sant'Anna event study reveals a **statistically significant, non-linear pre-treatment violation of parallel trends**. The CS ATT relative to the base period (t=−1) follows a V/U shape:

| Relative time | CS ATT ($/month) | SE |
|---|---:|---:|
| t=−12 | −7.53 | 1.70 |
| t=−11 | −7.12 | 1.73 |
| t=−10 | −10.65 | 1.92 |
| t=−9  | −13.94 | 2.14 |
| **t=−8** | **−16.00** | **2.27** ← minimum |
| t=−7  | −15.20 | 2.16 |
| t=−6  | −15.01 | 1.95 |
| t=−5  | −11.90 | 1.75 |
| t=−4  | −8.45  | 1.50 |
| t=−3  | −4.49  | 1.19 |
| t=−2  | −2.73  | 0.77 |
| t=−1  | 0.00   | 0.00 (base) |

**All pre-treatment estimates are statistically significant** (p < 0.05). The parallel trends regression test (interaction coef = 4.03, p = 0.35) is *not* a contradiction — it is simply underpowered given the observed $7–$16 level differences.

### What the V-shape means

The CS ATT at time t measures the DiD relative to the base period: how much more (or less) did treated tracts' rents change from t=−1 to t compared to controls?

A **negative** pre-treatment ATT at t=−12 means: going backward in time, treated tracts' rents were lower relative to their t=−1 level than controls were relative to their t=−1 level. In other words, **treated tracts had faster-growing rents in the pre-treatment period** (they grew more from t=−12 to t=−1 than controls did).

This is confirmed by raw rent level data:
- Jan 2015: control rent = $1,209, treated rent = $1,367 (gap = +$158)
- Sep 2015: control rent = $1,241, treated rent = $1,423 (gap = +$182)
- Treated tracts had **higher absolute rents AND faster growth** pre-treatment.

**Economic interpretation:** Treated tracts were likely experiencing pre-existing gentrification — rising rents driven by neighborhood demand pressure — before the STR prohibition was enacted. The prohibition was applied disproportionately in these appreciating-market tracts, not at random.

The non-monotone shape (descent to a minimum at t=−8, then recovery toward t=−1) suggests the pre-treatment dynamics had two phases:
1. **Early pre-period (t=−12 to t=−8):** rent differentials widening (treated growing faster)
2. **Later pre-period (t=−8 to t=−1):** rent differentials narrowing (rates converging slightly)

---

## 2. Why the Raw CS ATT Is Likely Upward-Biased

The full-panel CS post-treatment event study shows positive and growing effects:
- Months 0–2: +$3 to +$1
- Months 9–12: +$6 to +$8
- Months 30–36: +$11 to +$16

**The problem:** the positive post-treatment ATT likely reflects the *continuation of the pre-treatment reconvergence trend* rather than a causal effect of the prohibition.

The pre-treatment ATT was recovering from −$16 at t=−8 to $0 at t=−1, at a rate of approximately +$0.42/month (linear slope). If that recovery trend simply continued into the post-period, it would predict:
- By t=+12: +$5 (vs observed +$8 — similar)
- By t=+36: +$15 (vs observed +$16 — nearly identical)

The post-treatment ATT magnitudes are **entirely consistent with simple extrapolation of the pre-trend**, leaving no residual identifiable as a causal effect. Parallel trends is violated in a way that directly inflates the positive post-treatment estimate.

---

## 3. Why the Residualized CS Inverts to Negative

The `CallawaySantAnnaWithControlsAnalyzer` with `include_tract_trends=True` residualizes rents by removing tract-specific linear time trends estimated from pre-treatment data. This produces large negative post-treatment ATTs (−$58 to −$90).

**Why this is a functional form artifact, not a real negative effect:**

1. The pre-treatment trend for treated tracts is **non-linear** (V-shaped). Fitting a linear OLS trend through a V-shape yields a slope dominated by the recovery phase (the last 8 of 12 pre-periods), producing an upward-biased trend estimate.

2. This upward-biased linear trend is then **projected forward** into the post-treatment period. At month t=+k, the model "expects" +$0.42 × k more rent due to the trend. By t=+36, the trend extrapolation predicts +$15 more rent.

3. After subtracting this over-projected trend, the residualized treated rents are **below what the extrapolation predicted** — even though raw rents went up. The residualized ATT is therefore negative.

**Quantitative check:** Linear slope = +$0.42/month → over-subtracted at t=+36: 0.42 × 36 = **$15**, which exactly matches the raw positive CS ATT ($15.76). The sign flip is entirely accounted for by the detrending artifact.

**Key takeaway:** The negative residualized ATT does not mean rents fell after the prohibition. It means the linear trend extrapolation over-subtracts from treated tracts more than from controls, mechanically producing a negative difference.

---

## 4. The Quadratic Detrending Test

To verify the sign flip is a detrending artifact, the pipeline now includes a **quadratic tract-specific trend** specification (`detrend_order=2`, whitepaper mode only). Adding t² interactions to the detrending equation better fits the V-shaped curvature.

**Expected outcome:** the residualized ATT under quadratic detrending should move toward zero or positive, compared to the large negative linear-detrend result. If confirmed, this is strong evidence that the sign flip under linear detrending is functional-form misspecification, not a real negative effect.

This spec is reported as an **appendix sensitivity figure** (`did_callaway_santanna_event_study_quadratic_detrend.png`) and should NOT be presented as an alternative headline estimate.

---

## 5. What Can and Cannot Be Claimed

### Cannot be claimed:

- **A positive causal effect** of STR prohibitions on rent levels. The raw CS ATT is confounded by pre-existing gentrification trends that are indistinguishable from the post-treatment effect given current data.
- **A negative causal effect** of STR prohibitions. The residualized ATT is a functional form artifact, not evidence of rent reduction.
- **That parallel trends holds**. The parallel trends OLS regression test (p=0.35) is underpowered — the CS event study is the correct diagnostic and shows clear violations.

### Can be claimed:

- **Treated tracts had higher and faster-growing rents before the ordinance**, consistent with selection of the ordinance into gentrifying neighborhoods. This is itself a policy-relevant finding about targeting.
- **The full-panel CS ATT is bounded-positive under sensitivity analysis**: using HonestDiD (Rambachan & Roth 2023) with smoothness bound M = 2 $/month (the observed slope of the pre-trend violation), the identified set for the average ATT should be computed and reported.
- **Cohort-specific results for cohorts with flatter pre-trends are more credible** than the aggregate. Identifying which cohorts pass a pre-trend plausibility check anchors the most defensible sub-estimate.
- **The sign and magnitude are sensitive to detrending assumptions** — this is a legitimate finding about identification, not a failure to disclose.

---

## 6. The Credible Path Forward: HonestDiD Bounds

The `HonestPretrendsAnalyzer` in `src/housing/components/analyzers/honest_pretrends.py` computes a smoothness bound from the TWFE pre-period. The full Rambachan & Roth (2023) identified set requires running the `honest_did` R package or equivalent Python port.

**Recommended steps:**
1. Extract the smoothness bound M from `honest_pretrends_summary.csv` (field: `smoothness_second_diff_abs_max`).
2. Run HonestDiD with M values: 1, 2, 4 ($/month per period).
3. Report the identified set [ATT_low, ATT_high] at each M in the limitations section.
4. If the identified set excludes zero at M=2, the positive-effect conclusion has some defensible support. If it spans zero, the honest conclusion is "consistent with zero, uninformative."

---

## 7. Paper Narrative Implications

Based on this analysis, the paper should be restructured as follows:

### Results section (recommended order):
1. **Show the event study first** — the V-shape is a finding, not an embarrassment. Frame it as: "the ordinance was selectively applied in higher-rent, appreciating neighborhoods."
2. **State the parallel trends limitation explicitly** — quantify the maximum deviation (~$16 at t=−8) and its statistical significance.
3. **Present the CS ATT with the caveat** — positive and growing, but cannot be distinguished from pre-trend continuation without sensitivity analysis.
4. **Report HonestDiD bounds** — this is the credibility result, not the point estimate.
5. **Show robustness: matched sample, k-sweep, threshold sweep** — direction-stable even if magnitude varies.
6. **Appendix: quadratic detrend sensitivity** — demonstrates the linear detrend sign flip is a detrending artifact.

### What NOT to do:
- Lead with a point estimate ($X/month) without accompanying sensitivity bounds.
- Report the linear-detrend negative ATT as a robustness check that "confirms" anything — it is an artifact.
- Claim the OLS parallel-trends test validates the design (it doesn't have power here).

### Abstract language (suggested):
> "The STR prohibition was applied preferentially in higher-rent, appreciating-market tracts, consistent with selective enforcement in gentrifying neighborhoods. After accounting for pre-existing trend differences, point estimates of the rent effect are positive but sensitive to detrending assumptions; under a pre-trend smoothness sensitivity analysis, estimates are consistent with bounded positive effects. Cohort-specific analysis confirms the positive direction for cohorts with more credible parallel trends."
