# White paper (LaTeX)

Policy brief compiling causal evidence on Chicago STR prohibitions and rental outcomes.

## Build

Requirements: a LaTeX distribution with `latexmk`, `pdflatex`, and `bibtex` (`natbib` + `plainnat`).

From this directory:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

Or from repo root (`Makefile` exposes `make white-paper` if available).

Bibliography resolves to [`literature/references.bib`](../../literature/references.bib).

## Figures

Prefer copying pipeline outputs into `figures/` (ignored if large—track copies intentionally) so the PDF build is reproducible without regenerating pipelines. Paths in `main.tex` also include fallback search paths toward `output/did-cs/` when building from a checkout with generated outputs locally.
