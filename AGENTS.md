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

Docker / Make: [`Makefile`](Makefile)—`make run-did-pipeline-cs`; `run-did-pipeline-cs-local` copies `data/` to `/tmp` to avoid Box/cloud sync locks.

---

## Conventions agents should follow

1. Do **not** commit `data/`, `output/`, `.venv/`, caches, or `literature/**/*.pdf` unless intentionally using Git LFS.
2. Prefer small, scoped commits when changing analysis code or docs.
3. When editing causal components, skim [`docs/CS_WITH_CONTROLS.md`](docs/CS_WITH_CONTROLS.md) so narrative matches **residualization + CS** semantics.
4. White paper builds from [`docs/white-paper/main.tex`](docs/white-paper/main.tex); bibliography is [`literature/references.bib`](literature/references.bib)—update both when citing new work.
5. **ATT interpretation:** Effects are differences in rent **levels** in $/month (index-scale), not "dollars of change per elapsed calendar month" unless stated.

---

## Optional commands

```bash
make run-did-pipeline-cs         # Docker: full CS pipeline
make white-paper                 # Requires latexmk + TeX on host (outside Docker)
make test                       # pytest in container
```

---

## Planned exploratory extensions (paper branch)

Synthetic control / synthetic DiD and double ML are scoped as **possible extensions**; literature notes belong under [`literature/notes/`](literature/notes/README.md).
