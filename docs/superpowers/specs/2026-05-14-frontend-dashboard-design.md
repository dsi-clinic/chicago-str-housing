# Frontend Dashboard Design Spec
**Date:** 2026-05-14  
**Author:** Andrés F. Camacho  
**Project:** Chicago Housing STR Analysis — Data Story Frontend

---

## Goal

A locally-runnable Next.js data story site that presents the analysis pipeline results to an audience. White background, minimal, professional. No invented figures — all content sourced from existing pipeline outputs in `output/`.

---

## Architecture

- **Location:** `dashboard/` at repo root — standalone Next.js app, decoupled from Python pipeline
- **Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Data:** Static files from `output/did-cs-whitepaper-binary/` and `output/did-cs-whitepaper-threshold/` symlinked into `dashboard/public/data/binary/` and `dashboard/public/data/threshold/`
- **Figures:** Served as `<Image>` from `/data/binary/*.png` — no re-rendering
- **Stats/tables:** CSV files parsed at component mount via `fetch('/data/binary/*.csv')`, typed with Papaparse or hand-rolled parser
- **No backend:** Pure static + Next.js built-in file serving, `npm run dev` only

---

## Layout Shell

### Hero (always visible, above tabs)
- Title: "Impact of STR Prohibitions on Chicago Rental Prices"
- Subtitle: "Staggered Difference-in-Differences · Census Tract Level Analysis"
- Author block (right): Andrés F. Camacho · Data Science Clinic · University of Chicago · 2025
- Stats row: 5 pills reading live from `did_descriptive_panel_overview.csv` — tracts, months, observations, treated, never-treated

### Tab navigation (sticky below hero)
7 tabs in order: **Introduction · Descriptive · Analysis · Models · Robustness · Pre-trends · Policy**  
Active tab: maroon underline (#8B0000). Next.js App Router routes: `/`, `/descriptive`, `/analysis`, `/models`, `/robustness`, `/pretrends`, `/policy`

---

## Tab Designs

### 1. Introduction (`/`)
- Research question callout block (maroon left border)
- Story grid (2×2): The Problem · The Policy · Staggered Rollout · Research Question
- Treatment definition box: Binary vs Threshold side-by-side (blue / teal)
- Data cards row (centered, flex): 487 tracts · 128 months · 373 treated · 114 control · 62k obs
  - Each card reads its value from `did_descriptive_panel_overview.csv` + `did_descriptive_summary_stats.csv`
- Two-column info blocks: Pre-treatment rent balance + Panel coverage

### 2. Descriptive (`/descriptive`)
**Interactive 6-step pipeline** — `useState(activeStep)` in React:

| Step | Component | Tract count | Source |
|------|-----------|-------------|--------|
| 1 | All Chicago Tracts | 1,332 | hardcoded (shapefile) |
| 2 | ZIP→Tract Crosswalk | — | `ZipTractCrosswalkProcessor` |
| 3 | Rent Panel Match | 487 | `did_descriptive_panel_overview.csv` |
| 4 | STR Prohibition Dates → Tract | 487 retained | `tract_prohibition_dates.csv` |
| 5 | Treatment Assignment | 373+114 | `did_descriptive_summary_stats.csv` |
| 6 | Trend Matching & Pre-trend Filter | matched | `did_descriptive_panel_overview.csv` |

- Step 5 has Binary/Threshold toggle (`useState(treatMode)`)  
- Each step: left col = explanation + stat chips; right col = retention bar + figure slot  
- Figure slots inside right col of active step panel  
- Prev/Next nav buttons in footer  
- Below pipeline: `data_funnel.png` + `did_adoption_curve.png` + `did_parallel_trends.png`

### 3. Analysis (`/analysis`)
- Spatial maps row: `did_story_map.png`, `did_spatial_sample_ever_treated.png`, `did_story_map_cohort.png`
- Cohort stats table from `did_descriptive_cohort_stats.csv`
- Event study: `event_study_plot.png`
- Cohort dynamics: `did_cohort_dynamics.png`

### 4. Models (`/models`)
- Estimator explainer: TWFE vs CS side-by-side prose blocks
- CS with controls: `did_callaway_santanna_event_study.png`
- CS with controls + trends: `did_callaway_santanna_event_study_with_controls.png`
- TWFE vs CS comparison: `did_twfe_vs_cs_comparison.png` + `did_cs_twfe_difference.png`
- Comparison table from `did_twfe_cs_comparison_table.csv`
- Cohort dynamics with controls: `did_cohort_dynamics_with_controls.png`

### 5. Robustness (`/robustness`)
- Side-by-side: Binary (`/data/binary/`) vs Threshold (`/data/threshold/`) outputs
- Toggle or split view: `did_callaway_santanna_event_study.png` from both directories
- Cohort dynamics comparison: both treatment modes
- TWFE vs CS comparison: both modes

### 6. Pre-trends (`/pretrends`)
- Parallel trends plot: `did_parallel_trends.png`
- Honest pre-trends table from `honest_pretrends_summary.csv`
- Pre-trend regression summary from `pretrend_parallel_trends_regression_summary.csv`
- SUTVA: `sutva_donut.png` + `sutva_dose_response.png`
- Diagnostic: `did_diagnostic_analysis.png`

### 7. Policy (`/policy`)
- ATT summary: aggregate effect reading from `did_twfe_cs_comparison_table.csv` (rel_time ≥ 0)
- Cohort explainer: `cohort_dynamics_explainer.png`
- 3–4 prose policy conclusion blocks
- Limitations and next steps

---

## Data Layer

```
dashboard/
  public/
    data/
      binary/    → symlink to ../../output/did-cs-whitepaper-binary/
      threshold/ → symlink to ../../output/did-cs-whitepaper-threshold/
  src/
    app/
      layout.tsx        # Hero + TabNav shell
      page.tsx          # Introduction
      descriptive/page.tsx
      analysis/page.tsx
      models/page.tsx
      robustness/page.tsx
      pretrends/page.tsx
      policy/page.tsx
    components/
      Hero.tsx
      TabNav.tsx
      PipelineStepper.tsx   # Descriptive interactive pipeline
      DataCard.tsx
      FigureSlot.tsx        # <Image> wrapper with filename label
      StatTable.tsx         # Renders CSV rows as a table
    lib/
      csv.ts                # fetch + parse CSV util
      types.ts              # PanelOverview, SummaryStats, etc.
```

---

## Design Tokens
- Primary: `#8B0000` (maroon)
- Secondary: `#0D9488` (teal), `#2563EB` (blue), `#D97706` (amber)
- Background: `#ffffff` everywhere
- Border: `#eeeeee`
- Text: `#111111`, muted `#888888`
- Font: system-ui / Inter via Tailwind
- Radius: 12px cards, 8px buttons
- Shadow: `0 4px 16px rgba(0,0,0,0.05)`

---

## Constraints
- No invented figures — every image tag points to a real pipeline output file
- CSV values drive all stat cards — no hardcoded numbers in JSX
- `npm run dev` only, no deployment needed
- Add `dashboard/` and `.superpowers/` to `.gitignore` entries for `node_modules` and build artifacts
