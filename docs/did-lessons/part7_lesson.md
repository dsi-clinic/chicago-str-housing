# Part 7: Trend-Matched Sample Analysis

## Introduction

In Part 6, you estimated the event study and tested parallel trends. Often the pre-treatment coefficients are not flat—they show a trend or systematic differences between treated and control tracts. When that happens, the raw TWFE estimate may be confounded: what looks like a treatment effect could be pre-existing trend differences.

**Trend matching** addresses this by restricting the analysis to treated tracts plus control tracts with similar pre-treatment rent trends. You match on the pre-treatment slope (dollars per month), then re-run DiD on the matched sample. This lesson guides you to build the `TrendMatchingProcessor` component and a matched-sample pipeline from scratch.

---

## Why Trend Matching?

When pre-trends differ between treated and control groups:
- The "effect" can reflect pre-existing trend differences, not the policy
- Parallel trends is violated; the DiD estimate is biased
- Matching on pre-treatment rent slope makes groups more comparable *before* treatment

Trend matching does not fix parallel trends by itself, but it improves comparability. If the matched-sample estimate differs substantially from the full-panel estimate, that suggests the raw result was partly driven by trend differences.

---

## How Trend Matching Works

Three steps you will implement:

1. **Calculate pre-treatment trends:** For each tract, fit `rent ~ time` in the pre-period; extract the slope (dollars per month). Require at least `min_pre_periods` months of pre-treatment data. Skip tracts with insufficient pre-period.

2. **Match:** For each treated tract, find `k` nearest **never-treated** tracts by pre-trend slope (Euclidean distance, k-NN). Use `sklearn.neighbors.NearestNeighbors`.

3. **Create matched sample:** Keep only matched tracts; drop the rest. Return the updated `did_panel` for downstream components.

---

## Building the TrendMatchingProcessor

Create a new `DataProcessor` component (e.g. in `src/housing/components/processors/trend_matching.py`). Your component should:

1. Require `did_panel` in context
2. Calculate pre-treatment trends for each tract
3. Match treated tracts to never-treated controls
4. Filter the panel to matched tracts and update context
5. Return the matched panel (and optionally matching details)

### Step 1: Calculate Pre-Treatment Trends

Loop over tracts, filter to pre-treatment months (`month < first_treatment`), and fit `linregress(months_numeric, rental_price)` to get the slope. Use `scipy.stats.linregress`.

- Convert `month` to numeric for the regression (e.g. months since panel start, or `(month - month.min()).dt.total_seconds() / (30 * 24 * 3600)`).
- Skip tracts with fewer than `min_pre_periods` months of pre-treatment data.
- Store `tract_geoid`, `pre_trend_slope`, and `ever_treated` (from `treated.max() > 0` per tract) in a DataFrame.
- If no tracts have enough pre-periods, raise a clear `ValueError` suggesting to reduce `min_pre_periods` or use a longer panel.

### Step 2: Match Tracts

Split the trends DataFrame into treated vs. never-treated. Fit `NearestNeighbors` on the control slopes (use `control_trends[["pre_trend_slope"]].values`—NearestNeighbors expects 2D input). For each treated tract, call `nn.kneighbors([[slope]])`; it returns `(distances, indices)` where indices refer to rows in the control DataFrame.

- Use `n_neighbors=min(self.k_neighbors, len(control_trends))` in case there are fewer controls than k.
- Build a matching DataFrame with `treated_tract`, `control_tract`, and `distance` (one row per treated-control pair).

### Step 3: Create Matched Sample

Collect unique tract IDs from both `treated_tract` and `control_tract` in the matching records. Filter `did_panel` with `did_panel["tract_geoid"].isin(matched_tracts)` and return the filtered copy.

**Parameters:** Use `k_neighbors=3` and `min_pre_periods=6` as defaults. Ensure your processor inherits from `DataProcessor` and overwrites `did_panel` in context so downstream components use the matched sample.

---

## Building the Matched Pipeline

Create a new script (e.g. `did_matched_pipeline.py`) that:

1. Runs the standard DiD pipeline to obtain `did_panel` (or loads it from context)
2. Registers `TrendMatchingProcessor` first
3. Re-registers `DIDDescriptiveAnalyzer`, `DIDEstimator`, `EventStudyAnalyzer`, `DIDTrendsVisualizer`, and `EventStudyVisualizer`
4. Uses output paths with a `_matched` suffix (e.g. `did_estimation_results_matched.csv`) so matched results do not overwrite full-panel results

**Execution order:** trend_matching → did_descriptive → did_estimation → event_study_analysis → did_trends_visualization → event_study_visualization.

The `TrendMatchingProcessor` overwrites `did_panel` in context, so all downstream components automatically use the matched sample.

---

## Interpreting Results

Compare **unmatched** vs **matched** results:

- **TWFE coefficient:** Did it change in magnitude or sign?
- **Event study pre-treatment coefficients:** Are they flatter in the matched sample?
- **Event study plot:** Do pre-treatment coefficients sit closer to zero?

If trend matching shrinks or flips the effect, the full-panel estimate was likely driven partly by pre-existing trend differences. If results are similar, the main finding is more robust.

---

## Deliverable

1. **`TrendMatchingProcessor`** component in `src/housing/components/processors/`
2. **Matched pipeline script** that runs trend matching and re-analysis
3. Outputs with `_matched` suffix (e.g. `did_estimation_results_matched.csv`, `event_study_plot_matched.png`)
4. Brief interpretation: Did trend matching change the conclusion? Why?

---

## Next Steps

Part 8 explores **robustness checks and heterogeneity**—testing whether results hold under different specifications and whether some subgroups are affected more than others.
