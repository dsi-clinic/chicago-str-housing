# STR prohibition — paper and policy brief

This folder holds the long-form analysis write-up and a one-page policy brief for city leadership, plus **mirrored pipeline outputs** so they render or download on GitHub (`output/` stays gitignored).

| Document | Audience |
|---|---|
| [STR_PROHIBITION_PAPER.md](STR_PROHIBITION_PAPER.md) | Technical / policy staff (full results and methods) |
| [STR_POLICY_BRIEF.md](STR_POLICY_BRIEF.md) | City leadership (executive summary) |

## Sync from `output/did-cs/`

```bash
make sync-str-paper-figures
```

- **`figures/`** — all PNGs used in the paper (main CS, TWFE comparison, trajectory, full heterogeneity set, spillover, with-controls sensitivity, cohort dynamics).
- **`csv/`** — a smaller curated set of summary tables (TWFE vs CS table, heterogeneity summary, bootstrap, spillover summary, trajectory summary).

Larger or secondary tabular outputs stay under `output/did-cs/` after a local pipeline run.

Then commit updates under `figures/` and `csv/` when outputs change.
