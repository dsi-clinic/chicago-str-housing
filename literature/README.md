# Literature review workspace

Place **downloaded PDFs** in `literature/topic/` (substantive papers: STR regulation, rents, housing) or `literature/methods/` (causal inference, DiD, Callaway–Sant'Anna, synthetic control, double ML).

- **`references.bib`**: BibTeX database used by [`docs/white-paper/main.tex`](../docs/white-paper/main.tex). Commit this file when you add citations.
- **`notes/`**: Short reading notes—what each paper contributes to identification, methods, or policy framing.

## Git behavior

PDFs matching `literature/**/*.pdf` are listed in [.gitignore](../.gitignore). Commit bibliography and markdown notes only, unless your team adopts Git LFS for PDFs.

## Sourcing papers

Prefer open-access versions and author preprints. Use [Google Scholar](https://scholar.google.com) for discovery and your institution’s library for final PDFs.

## Core methods to curate (indicative)

| Theme | Examples |
| --- | --- |
| Staggered DiD / TWFE issues | Goodman-Bacon; de Chaisemartin & D’Haultfoeuille; Borusyak, Jaravel, Spiess |
| Group–time ATT | Callaway & Sant’Anna |
| Dynamic / event study | Sun & Abraham |
| Covariate / DR adjustment | Sant’Anna & Zhao |
| Synthetic methods | Abadie, Diamond, Hainmueller (SC); Arkhangelsky et al. (synthetic DiD) |
| High-dimensional controls | Chernozhukov et al. (double / debiased ML) |

Add matching entries to `references.bib` as you read.
