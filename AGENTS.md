# Repository context for coding agents

Chicago **housing** analytics for the Data Science Institute (DSI) clinic and the City of Chicago (DTI). The codebase combines exploratory EDA/clustering with **causal inference** on how **short-term rental (STR)** prohibitions under the Shared Housing Ordinance relate to **rental prices** at the census tract level.

Confirm `git remote -v`; ongoing work may use a personal fork/private copy (see project notes).

---

## Repository layout

| Area | Purpose |
| --- | --- |
| [`src/pipeline/`](/src/pipeline/) | Generic pipeline orchestration (`Pipeline`, `PipelineComponent`), config |
| [`src/housing/components/loaders`](/src/housing/components/loaders/) | Load STR prohibitions, ZORI rents, ACS, boundaries, Airbnb, … |
| [`src/housing/components/processors`](/src/housing/components/processors/) | Crosswalk ZIP→tract, prohibition dates, treatment indicators, trend matching, covariate merger |
| [`src/housing/components/analyzers`](/src/housing/components/analyzers/) | TWFE/event study; **Callaway & Sant'Anna** (basic + doubly robust with covariates + tract-specific linear trends) |
| [`src/housing/components/visualizers`](/src/housing/components/visualizers/) | DiD/event-study plots |
| [`src/housing/scripts/`](/src/housing/scripts/) | Runnable pipeline entrypoints (EDA, clustering, DiD variants) |
| [`docs/`](docs/) | Documentation ([`CS_WITH_CONTROLS.md`](docs/CS_WITH_CONTROLS.md), [`white-paper/`](docs/white-paper/README.md)) |
| [`literature/`](literature/) | BibTeX + reading notes (`*.pdf` gitignored—commit `references.bib` and markdown notes) |
| [`tests/`](tests/) | Pytests |
| [`data/`](data/), [`output/`](output/) | **Gitignored.** Local CSVs/shapefiles and generated plots; recreate via pipelines |

---

## Architecture

```text
Loads (APIs/files) → Processors (geospatial joins, tract panel) → Analyzers (DiD / CS) → Visualizers → output/
       ↑                                                                     ↑
 Pipeline.set_execution_order() chains components; context dict passes artifacts between steps.
```

- **Treatment:** First month a tract has STR prohibition adoption (derived from prohibited buildings aggregate).
- **Outcome:** Monthly rent proxy (e.g. ZORI interpolated to tract).
- **Design:** **Staggered DiD.** TWFE/event study compares to **Callaway & Sant'Anna** group-time ATTs (`CallawaySantAnnaAnalyzer`; [`callaway_santanna_with_controls.py`](src/housing/components/analyzers/callaway_santanna_with_controls.py) adds **pre-period-only** residualization: ACS covariates + tract-specific linear trends, then DR-style comparisons).
- **Sample restriction:** [`TrendMatchingProcessor`](src/housing/components/processors/trend_matching.py) matches treated to never-treated tracts by pre-treatment rent trend slope (**separate from** tract-level linear trends in the CS-with-controls estimator).

Important scripts:

- [`did_pipeline_callaway_santanna.py`](src/housing/scripts/did_pipeline_callaway_santanna.py): TWFE + CS + CS with controls → figures under configurable output (Docker: `/project/output/did-cs/`).

**Slide / whitepaper tree:** With `DID_WHITEPAPER_MODE=1` (or `make run-did-pipeline-cs-whitepaper`), outputs default to **`output/did-cs-whitepaper/`** and add pretrend heuristic, cohort explainer figure, spatial donut/dose diagnostics, and `tables/tab_*.tex`. See [`docs/DID_CS_RUNBOOK.md`](docs/DID_CS_RUNBOOK.md) and [`docs/white-paper/STORY_OUTLINE.md`](docs/white-paper/STORY_OUTLINE.md).
Docker / Make: [`Makefile`](Makefile)—`make run-did-pipeline-cs`; `run-did-pipeline-cs-local` copies `data/` to `/tmp` to avoid Box/cloud sync locks.

---

## Conventions agents should follow

1. Do **not** commit `data/`, `output/`, `.venv/`, caches, or `literature/**/*.pdf` unless intentionally using Git LFS.
2. Prefer small, scoped commits when changing analysis code or docs.
3. When editing causal components, skim [`docs/CS_WITH_CONTROLS.md`](docs/CS_WITH_CONTROLS.md) so narrative matches **residualization + CS** semantics.
4. White paper builds from [`docs/white-paper/main.tex`](docs/white-paper/main.tex); bibliography is [`literature/references.bib`](literature/references.bib)—update both when citing new work.
5. **ATT interpretation:** Effects are differences in rent **levels** in $/month (index-scale), not "dollars of change per elapsed calendar month" unless stated.

## DiD descriptive outputs (for slides / appendices)

After a successful [`did_pipeline_callaway_santanna.py`](src/housing/scripts/did_pipeline_callaway_santanna.py) run, **`output/did-cs/did_descriptive_*.csv`** are written by [`DIDDescriptiveAnalyzer`](src/housing/components/analyzers/did_descriptive.py), including panel coverage (balanced tract-month counts), adoption curves, pre-treatment balance rent table, tract-level coverage, and a mean-comparison \(t\)-test.

## Slides (`docs/white-paper/ppt`)

Beamer deck: [`docs/white-paper/ppt/presentation.tex`](docs/white-paper/ppt/presentation.tex) + `beamerthemeUChicago.sty` (DSI-inspired maroon styling; `\WPFig` placeholders if PNGs not built yet). Figures/tables `\input`/paths target **`../../../output/did-cs-whitepaper/`** by default (`make whitepaper-deck`). [`analysis/`](docs/white-paper/ppt/analysis/) retains CSV summaries for copy-paste.

## Local pipeline (no Docker)

Set `DATA_DIR` to your checkout’s `data/` folder; the script resolves **`DID_CS_OUTPUT_DIR`** to `output/did-cs` when not using `/project` paths. Example:

```bash
export PYTHONPATH=src
export DATA_DIR="$(pwd)/data"
.venv/bin/python src/housing/scripts/did_pipeline_callaway_santanna.py
```

---

## Optional commands

```bash
make run-did-pipeline-cs         # Docker: full CS pipeline
make white-paper                 # Requires latexmk + TeX on host (outside Docker)
make run-did-pipeline-cs-whitepaper   # Host: artefacts → output/did-cs-whitepaper
make whitepaper-deck             # Builds Beamer at docs/white-paper/ppt
make test                       # pytest in container
```

---

## Planned exploratory extensions (paper branch)

Synthetic control / synthetic DiD and double ML are scoped as **possible extensions**; literature notes belong under [`literature/notes/`](literature/notes/README.md).
