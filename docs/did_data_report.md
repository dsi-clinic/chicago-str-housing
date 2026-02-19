# DiD Panel Data Report

Diagnostic output from `make run-did-deep-diagnostic` on the Chicago STR prohibition dataset.

---

## 1. Panel Structure

| Dimension | Value |
|-----------|-------|
| Tracts | 842 |
| Months | 128 (Jan 2015 -- Aug 2025) |
| Total observations | 107,776 |
| Balance | Perfectly balanced (842 x 128) |
| Missing months in range | 0 |

The panel is a complete rectangle: every tract is observed in every month. No balancing or imputation is needed.

---

## 2. Treatment Design

**373 treated tracts** across **40 distinct treatment cohorts** (unique prohibition start months).
**469 tracts** are never-treated throughout the panel.

Treatment is heavily concentrated in mid-2016, coinciding with the initial wave of Chicago's STR prohibition ordinance:

| Cohort | Tracts | Pre-periods | Post-periods |
|--------|--------|-------------|--------------|
| 2016-08 | 119 | 19 | 109 |
| 2016-07 | 80 | 18 | 110 |
| 2019-10 | 39 | 57 | 71 |
| 2017-02 | 16 | 25 | 103 |
| 2016-09 | 13 | 20 | 108 |
| 2016-10 | 13 | 21 | 107 |
| 2018-04 | 9 | 39 | 89 |
| 2016-11 | 7 | 22 | 106 |
| 2017-03 | 7 | 26 | 102 |
| 2017-08 | 7 | 31 | 97 |

The remaining 30 cohorts have 1--5 tracts each. The staggering pattern has two peaks: the 2016 ordinance rollout (212 tracts in Jul--Aug 2016 alone) and an October 2019 wave (39 tracts).

---

## 3. STR Prohibition Data Quality

| Metric | Value |
|--------|-------|
| Total buildings in raw data | 2,292 |
| Date range | 2015-10-25 to 2025-11-26 |
| Records with date before 2015 | 1 (corrected to 2015-10-25 by loader) |

**Prohibitions by year:**

| Year | Buildings |
|------|-----------|
| 2015 | 2 |
| 2016 | 865 |
| 2017 | 794 |
| 2018 | 171 |
| 2019 | 280 |
| 2020 | 32 |
| 2021 | 60 |
| 2022 | 20 |
| 2023 | 15 |
| 2024 | 40 |
| 2025 | 13 |

72% of prohibitions (1,659 buildings) were enacted in 2016--2017. There is a secondary spike in 2019 (280 buildings). Only 1 record had an anomalous pre-2015 date, which the `STRProhibitionDataLoader` automatically corrects.

---

## 4. Rental Price Summary

**Annual averages by treatment group:**

| Year | Never-treated | Treated |
|------|--------------|---------|
| 2015 | $1,172 | $1,378 |
| 2016 | $1,184 | $1,419 |
| 2017 | $1,198 | $1,453 |
| 2018 | $1,215 | $1,485 |
| 2019 | $1,238 | $1,528 |
| 2020 | $1,254 | $1,534 |
| 2021 | $1,285 | $1,562 |
| 2022 | $1,365 | $1,690 |
| 2023 | $1,438 | $1,795 |
| 2024 | $1,534 | $1,889 |
| 2025 | $1,632 | $1,992 |

**Never-treated tract statistics:**
- Mean rent: $1,310
- Std dev: $297

**Baseline gap:** Treated tracts start ~$200 higher than never-treated ($1,378 vs $1,172 in 2015), a ~18% difference. Both groups trend upward over the panel. This level difference is expected -- STR prohibitions target areas with higher tourist/rental demand.

**Outlier check:**
- IQR: $506 (Q1=$1,199, Q3=$1,706)
- Low outliers (< $440): 0 tracts
- High outliers (> $2,466): 0 tracts

No extreme outlier tracts by the 1.5x IQR criterion.

---

## 5. Pre-Treatment Parallel Trends

Comparing the first 24 months (Jan 2015 -- Dec 2016) for tracts *before* their treatment date:

| Group | First month | Last month | Growth |
|-------|-------------|------------|--------|
| Never-treated | $1,165 | $1,184 | +1.6% |
| Treated (pre-treat only) | $1,344 | $1,275 | -5.2% |

The treated group shows a **declining** pre-treatment trend while the never-treated group is roughly flat. This divergence is a concern for the parallel trends assumption: it means the treated and never-treated groups were *not* trending in the same direction before treatment.

Possible explanations:
- **Composition effect**: most treated tracts begin treatment in mid-2016, so the "treated, pre-treatment" window is very short (only 6--18 months for the bulk of the sample). With few pre-periods, a handful of high-rent tracts dropping could drive the average down.
- **Anticipation effects**: landlords or markets may have adjusted in advance of the prohibition.

This should be investigated further with event study plots and formal pre-trend tests.

---

## 6. Relative Time Distribution (Treated Tracts)

| Relative time bin | Observations |
|-------------------|-------------|
| < -36 months | 1,822 |
| -36 to -24 | 1,222 |
| -24 to -12 | 3,268 |
| -12 to -6 | 2,232 |
| -6 to -1 | 1,865 |
| -1 to 0 | 373 |
| 0 to 5 | 2,238 |
| 6 to 11 | 2,236 |
| 12 to 23 | 4,404 |
| 24 to 35 | 4,404 |
| 36+ | 23,680 |

Most treated-tract observations (23,680 / 47,744 = 50%) fall at 36+ months post-treatment, reflecting the early treatment dates and long panel. There are relatively few deep pre-treatment observations because the 2016 cohorts only have ~18 months of pre-data.

---

## 7. What Each Estimator Does

### TWFE (Two-Way Fixed Effects)

The standard `Y = alpha_i + gamma_t + beta * D_it + epsilon` regression with tract and time fixed effects. Under staggered treatment:

- TWFE uses already-treated units as implicit controls for later-treated units
- This creates **negative weighting** on some group-time ATTs, biasing the overall estimate when treatment effects are heterogeneous over time or across cohorts
- With 40 cohorts and a 10-year panel, this bias risk is substantial

### Callaway-Sant'Anna (2021)

Estimates separate ATT(g,t) for each cohort `g` at each time `t`, using only never-treated (or not-yet-treated) units as controls. Aggregation to a single ATT is done with explicit, non-negative weights.

- Avoids the "forbidden comparison" problem
- Requires sufficient cohort sizes for stable estimation
- Allows group-specific and calendar-time-specific effect heterogeneity

The comparison between TWFE and CS reveals whether treatment effect heterogeneity is distorting the TWFE estimate. If they agree, the standard TWFE is adequate. If they diverge, CS is the more credible estimator.

---

## 8. Callaway-Sant'Anna Estimation Feasibility

| Min cohort size | Valid cohorts | Tracts covered |
|----------------|---------------|----------------|
| 5 | 12 | 320 |
| 10 | 6 | 280 |
| 20 | 3 | 238 |

**Never-treated comparison pool: 469 tracts**

The comparison pool (469 tracts) is large relative to any individual cohort. The 6 cohorts with >= 10 tracts cover 280 of the 373 treated tracts (75%). The 3 largest cohorts alone (2016-07, 2016-08, 2019-10) cover 238 tracts (64%).

Cohorts with only 1--4 tracts will produce noisy ATT(g,t) estimates and may need to be dropped or grouped. A practical approach is to set `min_cohort_size=5` or `min_cohort_size=10` when running the CS estimator.

---

## 9. Panel Balance

The panel is confirmed **perfectly balanced**: 842 tracts x 128 months = 107,776 observations with no gaps. No balancing, trimming, or imputation is required before estimation.

---

## 10. Summary of Key Facts

| Fact | Value |
|------|-------|
| Panel dimensions | 842 tracts x 128 months |
| Treated tracts | 373 |
| Never-treated tracts | 469 |
| Treatment cohorts | 40 |
| Cohorts with >= 10 tracts | 6 |
| Date range | Jan 2015 -- Aug 2025 |
| Mean rent (overall) | ~$1,438 |
| Baseline rent gap (treated - never-treated) | ~$200 (18%) |
| Pre-treatment trend concern | Treated group declining while control flat |
| Panel balance | Perfect -- no gaps |
| STR buildings | 2,292 |
| STR date anomalies | 1 (auto-corrected) |
