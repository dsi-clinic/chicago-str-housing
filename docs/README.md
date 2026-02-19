# Documentation Index

## Quick Start Guides

### For Students
- **[DID Student Plan](DID_STUDENT_PLAN.md)** - Complete learning curriculum for DiD analysis
- **[Part 1: Causal Inference](did-lessons/part1_lesson.md)** - Introduction to causality and research design
- **[Part 2: Panel Data](did-lessons/part2_lesson.md)** - Working with panel datasets
- **[Part 3: Treatment Indicators](did-lessons/part3_lesson.md)** - Creating treatment variables
- **[Part 4: Event Studies](did-lessons/part4_lesson.md)** - Event study methodology

### For Researchers
- **[DiD Estimator Comparison](did_estimator_comparison.md)** - Quick reference: TWFE vs. Callaway-Sant'Anna
- **[Callaway-Sant'Anna Guide](callaway_santanna_guide.md)** - Complete implementation guide

## Methodology Documentation

### Difference-in-Differences (DiD)

#### Standard TWFE Approach
- **Implementation**: `src/housing/components/analyzers/event_study.py`
- **Pipeline**: `make run-did-pipeline`
- **Use when**: Single treatment timing OR as robustness check

#### Callaway & Sant'Anna (2020) Robust Estimator
- **Implementation**: `src/housing/components/analyzers/callaway_santanna.py`
- **Pipeline**: `make run-did-pipeline-cs`
- **Use when**: Staggered treatment with potential heterogeneous effects

### Key Concepts

**Staggered DiD**
- Treatment adopted at different times by different units
- Creates complex comparison groups
- TWFE may be biased if effects are heterogeneous

**Heterogeneous Treatment Effects**
- Effects differ by cohort (early vs. late adopters)
- Effects differ by time since treatment (dynamic)
- Effects differ by unit characteristics

**Negative Weighting Problem**
- TWFE implicitly uses already-treated units as controls
- Can produce biased or even wrong-signed estimates
- CS estimator avoids this by construction

## Quick Decision Guide

```
Do you have staggered treatment adoption?
├─ NO  → Use TWFE (EventStudyAnalyzer)
└─ YES → Use Callaway-Sant'Anna (CallawaySantAnnaAnalyzer)
          + Show TWFE as robustness check
```

## Pipeline Commands

| Analysis Type | Command | Description |
|---------------|---------|-------------|
| Basic EDA | `make run-eda-pipeline` | Exploratory data analysis |
| Clustering | `make run-clustering-analysis` | Spatial clustering |
| DiD (TWFE) | `make run-did-pipeline` | Standard event study |
| DiD + Covariates | `make run-did-pipeline-covariates` | With controls |
| DiD + CS | `make run-did-pipeline-cs` | Robust staggered DiD |

For local runs (avoiding Box/cloud drive issues), append `-local` to any command:
```bash
make run-did-pipeline-cs-local
```

## Output Files

### Standard DiD (TWFE)
```
output/
├── did_event_study.png
├── did_trends_by_group.png
└── did_summary_statistics.csv
```

### Callaway-Sant'Anna
```
output/
├── did_callaway_santanna_event_study.png    # Main results
├── did_twfe_vs_cs_comparison.png            # Compare estimators
├── did_cs_twfe_difference.png               # Bias visualization
├── did_cohort_dynamics.png                  # By-cohort effects
└── did_twfe_cs_comparison_table.csv         # Detailed table
```

## Key References

### Foundational Papers

1. **Angrist & Pischke (2009)** - *Mostly Harmless Econometrics*
   - Classic DiD and fixed effects

2. **Goodman-Bacon (2021)** - "Difference-in-differences with variation in treatment timing"
   - Journal of Econometrics 225.2: 254-277
   - Decomposition of TWFE estimator

3. **Callaway & Sant'Anna (2021)** - "Difference-in-differences with multiple time periods"
   - Journal of Econometrics 225.2: 200-230
   - Robust estimator for staggered DiD

4. **Sun & Abraham (2020)** - "Estimating dynamic treatment effects in event studies"
   - Journal of Econometrics 225.2: 175-199
   - Interaction-weighted estimator

5. **Roth et al. (2023)** - "What's trending in difference-in-differences?"
   - arXiv preprint
   - Comprehensive review of modern methods

### Applied Examples

6. **Airbnb Activity and Rental Markets** - Airbnb Research
   - Real-world application to short-term rentals

## Common Issues and Solutions

### Error: "Resource deadlock avoided (Errno 35)"
**Cause**: Data files on cloud-synced folder (Box, Dropbox, etc.)
**Solution**: Use `-local` variants of commands or set `DATA_DIR`:
```bash
make run-did-pipeline-cs-local
# or
DATA_DIR=/tmp/chicago_data make run-did-pipeline-cs
```

### Warning: "No comparison units for cohort X"
**Cause**: No never-treated units available
**Solution**: Switch to not-yet-treated comparison:
```python
CallawaySantAnnaAnalyzer(comparison_group="notyettreated")
```

### Issue: Wide confidence intervals in CS
**Not an error**: CS is more conservative (honest about uncertainty)
**Explanation**: Fewer comparison units, more careful inference

### Issue: TWFE and CS differ substantially
**Not an error**: Indicates heterogeneous treatment effects
**Action**: Trust CS estimates, investigate cohort-specific patterns

## Code Structure

```
src/housing/
├── components/
│   ├── analyzers/
│   │   ├── event_study.py              # TWFE event study
│   │   ├── callaway_santanna.py        # CS estimator
│   │   ├── did_descriptive.py          # Descriptive stats
│   │   └── pretrend_diagnostic.py      # Parallel trends tests
│   ├── visualizers/
│   │   ├── event_study.py              # TWFE plots
│   │   ├── callaway_santanna.py        # CS plots
│   │   └── did_trends.py               # Trend plots
│   ├── loaders/
│   │   └── time_series_rental_data.py  # Panel data loader
│   └── processors/
│       ├── treatment_indicator.py       # Treatment variables
│       └── time_series_zip_to_tract.py  # Geographic conversion
└── scripts/
    ├── did_pipeline.py                  # Basic DiD pipeline
    └── did_pipeline_callaway_santanna.py # TWFE + CS comparison
```

## Getting Help

1. **Check documentation**: Start with relevant guide above
2. **Review code comments**: All components have detailed docstrings
3. **Read original papers**: Especially CS (2021) and Goodman-Bacon (2021)
4. **Consult with mentor**: For interpretation questions
5. **Open GitHub issue**: For bugs or feature requests

## Contributing

When adding new components or documentation:

1. Follow existing code structure and style
2. Add comprehensive docstrings
3. Include references to papers/methods
4. Create examples and tutorials
5. Update this README with new content

## License

This project is for educational purposes as part of the Data Science Clinic at the University of Chicago.

## Contact

For questions about the analysis or methodology:
- Project mentor: [Contact info]
- Course staff: [Contact info]

---

Last updated: 2026-02-12
