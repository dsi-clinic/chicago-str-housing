# Beamer slides (presentation)

LaTeX **Beamer** sources for stakeholder or methods talks—parallel track to [`../main.tex`](../main.tex) (article/policy brief).

## Layout

| Path | Role |
| --- | --- |
| [`presentation.tex`](presentation.tex) | Main Beamer file (minimal Metropolis-compatible theme placeholders) |
| [`sections/*.tex`](sections/) | One file per logical slide block |
| [`snippets/`](snippets/) | Reusable `\input` fragments (titles, disclaimers) |
| [`analysis/`](analysis/) | Symlinks/copies toward `output/did-cs/*.csv` for referencing table numbers |

## Build

Requires a TeX install with **`beamer`** and **`latexmk`**:

```bash
cd docs/white-paper/ppt
latexmk -pdf -interaction=nonstopmode presentation.tex
```

## Figures

Prefer symlinks into `../../../../../output/did-cs/` PNGs **or** copy stable figures into `assets/` once outputs are finalized (so Dropbox paths do not surprise collaborators).
