## Summary

Lock a **single preferred specification** for the paper (default `k`, threshold percentile, primary estimator: CS baseline vs CS with controls, matched vs full-panel if both are shown). Present **primary results** under that spec, with **treatment-definition robustness** (threshold vs binary via `DID_TREATMENT_MODE` / dual output dirs) and the **k** and **percentile** sweeps as secondary robustness (separate issues).

Treat the **Next.js dashboard** on branch [`AFC/dashboard`](https://github.com/dsi-clinic/chicago-str-housing/tree/AFC/dashboard) as a **companion** to the paper (methodology audit, Love plots, lineage)—not the primary archival surface for estimates. The UI is intentionally **not** on `main`; sync it periodically from `main` for pipeline output paths.

## Deliverables

- [ ] One-page “**Preferred specification**” in repo docs (e.g. [`docs/DID_CS_RUNBOOK.md`](docs/DID_CS_RUNBOOK.md) or [`docs/methodology-audit/README.md`](docs/methodology-audit/README.md)): exact env vars, `k_neighbors`, percentile, comparison group, `min_cohort_size`, output folder convention (`did-cs-whitepaper-threshold` vs `-binary`).
- [ ] Paper text: “Preferred spec” box or footnote; robustness sections point to sweeps.
- [ ] Dashboard: no requirement to mirror every sweep; link or short note to where sweep tables live (`docs/` paths).

## Related issues

- Paper narrative: naive → preferred (separate issue).
- k_neighbors 1–5 sweep.
- Threshold percentile sensitivity.

## Notes

- Full-panel vs matched-only headline: align with advisor “naive first” issue—if full-panel CS is primary for identification narrative, state explicitly and keep matching as robustness.
