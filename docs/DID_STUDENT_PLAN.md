# DiD Analysis Student Plan

## Overview

This plan guides you through implementing a **Difference-in-Differences (DiD) analysis** to estimate the causal effect of STR prohibitions on rental prices. The plan is designed for students with **no prior exposure to causal inference or DiD**.

**Research Question:** *"What is the causal effect of STR prohibition adoption on rental prices in Chicago census tracts?"*

---

## Learning Objectives

By the end of the project, you will be able to:
1. **Understand** the DiD identification strategy and its assumptions
2. **Build** panel datasets from time series data
3. **Implement** two-way fixed effects models in Python
4. **Conduct** event study analysis to test parallel trends
5. **Interpret** causal effect estimates and assess their validity
6. **Visualize** treatment effects and diagnostic plots

---

## Prerequisites

Before starting, you should have:
- Completed the basic EDA pipeline (`housing_eda_pipeline.py`)
- Completed the clustering analysis (`clustering_analysis.py`)
- Understanding of the pipeline framework
- Basic Python skills (pandas, numpy, matplotlib)
- Comfortable with DataFrames, filtering, merging

---

## Project Parts

### **Part 1: Causal Inference & Research Design**

**Goal:** Understand causality and why we need DiD

**Part A: Causal Inference Primer**
1. **What is causality?**
   - Read: "Correlation vs. Causation"
   - Examples: Smoking → cancer, Education → income
   - Identify causal vs. correlational claims

2. **Why correlation ≠ causation:**
   - Confounding variables
   - Reverse causality
   - Selection bias
   - Find confounders in examples

3. **Identification strategies:**
   - Randomized experiments (gold standard)
   - Natural experiments
   - DiD as a natural experiment
   - Identify identification strategy in research papers

**Part B: DiD Conceptual Introduction**
1. **Simple 2×2 DiD example:**
   - Treatment group: 2 tracts
   - Control group: 2 tracts
   - Before period: 2015
   - After period: 2016
   - Calculate DiD by hand
   - Understand: Why we need both groups AND both periods

2. **Parallel trends assumption:**
   - Visual: Two lines that are parallel before treatment
   - What if they're not parallel?
   - Why this assumption matters

3. **Staggered DiD:**
   - What if treatment happens at different times?
   - Why it's more complex
   - How we handle it

**Deliverable:**
- 2-page document: "Understanding Causal Inference and DiD"
- Answers: What is causality? Why DiD? What is parallel trends?
- Hand-calculated 2×2 DiD example

---

### **Part 2: Panel Data & Infrastructure**

**Goal:** Learn panel data manipulation, then build infrastructure

**Part A: Panel Data**
1. **What is panel data?**
   - Cross-section vs. time series vs. panel
   - Examples: (person, year), (tract, month)
   - Why we need it for DiD

2. **Pandas panel data skills:**
   - Reshaping: `pd.melt()` (wide → long)
   - Multi-index DataFrames
   - Grouping by entity and time

3. **Example code:**
   ```python
   # Example: Reshape wide to long
   wide_df = pd.read_csv("data.csv")
   date_cols = [col for col in wide_df.columns if col.startswith("20")]
   long_df = wide_df.melt(
       id_vars=["zip_code"],
       value_vars=date_cols,
       var_name="month",
       value_name="rental_price"
   )
   ```

**Part B: Build Time Series Loader**
1. **Create the loader component:**
   - Build: `TimeSeriesRentalLoader` component
   - Tasks: Load CSV, identify date columns, reshape to long format
   - Test with small subset first
   - Output: ZIP-level panel `(zip_code, month, rental_price)`

2. **Incremental development:**
   - Step 1: Load CSV
   - Step 2: Identify date columns
   - Step 3: Reshape to long
   - Step 4: Test and validate

**Part C: Convert ZIP to Tract**
1. **Why convert to tract level?**
   - STR prohibitions are tracked at the census tract level
   - DiD analysis requires matching treatment assignment geography
   - ZIP codes and tracts don't align perfectly — need spatial interpolation

2. **Create the processor component:**
   - Build: `TimeSeriesZipToTractProcessor` component
   - Uses ZIP→tract crosswalk with area weights
   - Apply crosswalk to each month's data
   - Output: Tract-level panel `(tract_geoid, month, rental_price)`

**Deliverable:**
- `TimeSeriesRentalLoader` component
- `TimeSeriesZipToTractProcessor` component
- Panel dataset: `output/rental_panel_data.csv` with columns: `tract_geoid`, `month`, `rental_price`

---

### **Part 3: Treatment Indicators**

**Goal:** Create treatment variables

**Part A: Understanding Treatment Indicators**
1. **What is a treatment indicator?**
   - Binary: 0 = not treated, 1 = treated
   - When does it switch from 0 to 1?
   - Visual: Timeline for one tract

2. **Example approach:**
   ```python
   # Example: Create treatment indicator
   def create_treatment_indicator(panel_df, treatment_dates):
       # Merge prohibition dates
       merged = panel_df.merge(treatment_dates, on="tract_geoid", how="left")
       
       # Create treated indicator
       merged["treated"] = (
           merged["month"] >= merged["first_prohibition_date"]
       ).astype(int)
       
       return merged
   ```

**Part B: Build Components**
- Build the `TreatmentIndicatorProcessor` component
- Focus on understanding the logic
- Test with small subset

**Deliverable:**
- `TreatmentIndicatorProcessor` component
- Final panel: `output/did_panel_data.csv` with columns:
  - `tract_geoid`, `month`, `rental_price`, `treated`, `months_since_treatment`
- Validation: Check that treated tracts switch at the right time

---

### **Part 4: Descriptive Analysis**

**Goal:** Understand the data before estimation

**Tasks:**
1. **Descriptive statistics:**
   - Create: `DIDDescriptiveAnalyzer` component
   - Calculate: Mean rental prices by treatment status over time
   - Calculate: Number of treated vs. control tracts by month

2. **Visualize trends:**
   - Create: `DIDTrendsVisualizer` component
   - Plot: Average rental prices for treated vs. control tracts over time
   - Plot: Number of treated tracts over time (adoption curve)

3. **Pre-treatment comparison:**
   - Compare: Treated vs. control tracts in pre-treatment period
   - Test: Are they similar on observables? (rental prices, demographics)
   - Document: Any pre-existing differences

**Deliverable:**
- `DIDDescriptiveAnalyzer` component
- `DIDTrendsVisualizer` component
- Report: "Pre-Treatment Descriptive Analysis" with plots and summary statistics

**Key Questions to Answer:**
- Do treated and control tracts have similar rental prices before treatment?
- Are there pre-existing trends that differ between groups?
- How many tracts get treated over time?

---

### **Part 5: Fixed Effects Deep Dive + Basic DiD**

**Goal:** Understand fixed effects, then estimate DiD

**Part A: Fixed Effects**
1. **What are fixed effects?**
   - Simple example: Controlling for time-invariant characteristics
   - Visual: What fixed effects "remove"
   - Why we need them for DiD

2. **Tract fixed effects:**
   - What they control for: Time-invariant tract characteristics
   - Example: "Lakefront location" is constant, so FE removes it
   - Identify what tract FE control for

3. **Time fixed effects:**
   - What they control for: City-wide trends
   - Example: "2016 housing boom" affects all tracts
   - Identify what time FE control for

4. **Two-way fixed effects:**
   - Both tract AND time FE
   - What's left? Within-tract variation over time
   - This is what we use for DiD

**Part B: Basic DiD Estimation**
1. **Estimate the model:**
   ```python
   # Example: Basic DiD
   from linearmodels import PanelOLS
   
   # Set panel index
   panel_data = df.set_index(['tract_geoid', 'month'])
   
   # Estimate
   model = PanelOLS.from_formula(
       'rental_price ~ 1 + treated',
       data=panel_data,
       entity_effects=True,  # Tract FE
       time_effects=True     # Time FE
   )
   results = model.fit(cov_type='clustered', cluster_entity=True)
   ```

2. **Interpretation:**
   - What does the coefficient mean?
   - What do the standard errors tell us?
   - Is the effect statistically significant?

**Deliverable:**
- `DIDAnalyzer` component
- Results table: Treatment effect estimate with standard errors
- Interpretation: 1-paragraph summary of main finding

---

### **Part 6: Event Study Analysis**

**Goal:** Estimate dynamic treatment effects and test parallel trends

**Tasks:**
1. **Create relative time indicators:**
   - Extend: `TreatmentIndicatorProcessor` to create dummies for each relative time period
   - Create: `rel_time_k` for k = -12, -11, ..., -1, 0, 1, ..., 12
   - Omit: One period (typically -1, the month before treatment) as reference

2. **Estimate event study:**
   - Create: `EventStudyAnalyzer` component
   - Model: `rental_price ~ Σ_k β_k(rel_time_k) + tract_FE + month_FE`
   - Extract: Coefficients for each relative time period

3. **Visualize event study:**
   - Create: `EventStudyVisualizer` component
   - Plot: Treatment effect coefficients vs. months since treatment
   - Add: 95% confidence intervals
   - Mark: Pre-treatment period (should be flat ≈ 0)

4. **Test parallel trends:**
   - Statistically test: Are pre-treatment coefficients jointly zero?
   - Visually assess: Is the pre-treatment line flat?

**Deliverable:**
- `EventStudyAnalyzer` component
- `EventStudyVisualizer` component
- Event study plot with pre-treatment coefficients
- Interpretation: "Do we have parallel trends? What is the dynamic treatment effect?"

**Key Questions:**
- Are pre-treatment coefficients ≈ 0? (parallel trends test)
- When does the effect appear? (immediate vs. lagged)
- Does the effect grow, shrink, or stabilize over time?

---

### **Part 7: Robustness Checks & Heterogeneity**

**Goal:** Test robustness and explore heterogeneous effects

**Tasks:**
1. **Robustness checks:**
   - Different time windows: Exclude early/late months
   - Different control groups: Only never-treated tracts vs. not-yet-treated tracts
   - Different specifications: Log prices vs. levels

2. **Heterogeneous effects:**
   - Create: `HeterogeneousEffectsAnalyzer`
   - Split by: High vs. low Airbnb density tracts
   - Split by: High vs. low income tracts (from census data)
   - Estimate: Interaction terms: `treated × high_airbnb_density`

3. **Visualize heterogeneity:**
   - Plot: Treatment effects by subgroup
   - Compare: Are effects stronger in some groups?

**Deliverable:**
- Robustness check results table
- Heterogeneous effects analysis
- Interpretation: "Are results robust? Do effects differ by neighborhood type?"

---

### **Part 8: Final Analysis & Report**

**Goal:** Synthesize all results into a final report

**Tasks:**
1. **Compile results:**
   - Main DiD estimate
   - Event study results
   - Robustness checks
   - Heterogeneous effects

2. **Write final report:**
   - Introduction: Research question and motivation
   - Data: Description of panel data construction
   - Methods: DiD identification strategy and assumptions
   - Results: Main findings with tables and figures
   - Discussion: Interpretation, limitations, policy implications

3. **Create presentation:**
   - 10-15 slide presentation
   - Key findings
   - Visualizations
   - Policy implications

**Deliverable:**
- Final report (8-10 pages)
- Presentation slides
- All code and outputs in organized format

---

## New Components to Build

**Loaders:**
- `TimeSeriesRentalLoader` - Load all monthly rental data

**Processors:**
- `TimeSeriesZipToTractProcessor` - Convert ZIP panel to tract panel
- `TractProhibitionDatesProcessor` - Aggregate prohibition dates to tract level
- `TreatmentIndicatorProcessor` - Create treatment variables

**Analyzers:**
- `DIDDescriptiveAnalyzer` - Descriptive statistics
- `DIDAnalyzer` - Main DiD estimation
- `EventStudyAnalyzer` - Event study estimation (stretch)
- `HeterogeneousEffectsAnalyzer` - Subgroup analysis (stretch)

**Visualizers:**
- `DIDTrendsVisualizer` - Pre-treatment trends
- `EventStudyVisualizer` - Event study plot (stretch)
- `HeterogeneityVisualizer` - Subgroup comparisons (stretch)

---

## Success Criteria

A successful project will:
1. Understand causal inference concepts
2. Understand DiD identification strategy
3. Work with panel data
4. Estimate basic DiD model
5. Interpret results correctly
6. Event study (stretch)
7. Robustness checks (stretch)
8. Write clear report

---

## Resources

- **Causal Inference Reference Guide** - [The Decision Lab](https://thedecisionlab.com/reference-guide/statistics/casual-inference) - Introduction to causal inference concepts, methods, and applications
- **An Introduction to Difference-in-Difference Analysis** - [Tilburg Science Hub](https://www.tilburgsciencehub.com/topics/Analyze/causal-inference/did/canonical-did-table/) - Step-by-step guide to the canonical 2×2 DiD table with examples
- **Difference-in-Differences** - [Causal Inference: The Mixtape](https://mixtape.scunning.com/09-difference_in_differences) - Comprehensive online chapter on DiD methods, assumptions, and applications
- **Airbnb Activity and Rental Markets in Canada** - [Airbnb Research](https://airbnb.app.box.com/s/rz7dhxs3kf095tjl36pjbisp50ddltjs) - Study examining the relationship between Airbnb activity and rental markets
- **Mostly Harmless Econometrics: An Empiricist's Companion** by Angrist & Pischke - [ResearchGate](https://www.researchgate.net/publication/51992844_Mostly_Harmless_Econometrics_An_Empiricist's_Companion) - Comprehensive guide to causal inference methods including DiD (see Chapter 5)


