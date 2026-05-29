# Staggered DiD toolkit — takeaway bullets

Purpose: shorthand for method choices embodied in [`did_pipeline_callaway_santanna.py`](../../src/housing/scripts/did_pipeline_callaway_santanna.py).

- **TWFE pooling risk:** Two-way FE with staggered rollout can implicitly compare already-treated cohorts (“forbidden contrasts”) when heterogeneous dynamic effects prevail (Goodman-Bacon 2021) — motivates transparent group–time ATTs rather than pooled TWFE reliance alone.

- **Callaway–Sant'Anna (2021):** Explicit cohort- and horizon-specific ATTs summarized in event curves; preferable to pooled TWFE when adoption is staggered and effects differ by cohort/time.

- **Parallel trends & relaxation:** Narrative distinguishes pre-period slope diagnostics, baseline covariate balance, and tract-linear residualization on pre-prohibition observations (see `docs/CS_WITH_CONTROLS.md` and `docs/PRETREND_VIOLATIONS_AND_FIXES.md`).

- **Sant'Anna–Zhao DR versus Double ML:** “Doubly robust” in [`callaway_santanna_with_controls.py`](../../src/housing/components/analyzers/callaway_santanna_with_controls.py) refers to outcome/IPW combos on staggered timelines; orthogonal-score Double ML (`econml` / `DoubleML`) is a different literature.

- **Synthetic / Synth-DiD complements:** Arkhangelsky et al. (2021); Abadie et al. (2010) classical synthetic controls for narrow scopes — scaffolded under `docs/exploratory/`.
