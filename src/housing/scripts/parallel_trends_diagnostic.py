"""Parallel trends diagnostic for the CS estimator."""

import sys
sys.path.insert(0, "src")

import logging
import numpy as np
from scipy import stats

logging.basicConfig(level=logging.WARNING)

from housing.scripts.did_pipeline_deseasonalized import run_did_analysis_deseasonalized

pipeline, ctx = run_did_analysis_deseasonalized()

print("=" * 80)
print("PARALLEL TRENDS DIAGNOSTIC")
print("=" * 80)

# 1. Event study pre-treatment analysis (WITH controls/DR)
es = ctx.get("cs_event_study")
if es is not None and not es.empty:
    pre = es[es["rel_time"] < 0].copy()
    post = es[es["rel_time"] >= 0].copy()

    print("\n--- EVENT STUDY: WITH CONTROLS (DR + tract trends) ---")
    print(f"Pre-treatment periods: {len(pre)}")
    print(f"Post-treatment periods: {len(post)}")
    print()
    print("Pre-treatment ATTs (should be ~0 for parallel trends):")
    for _, r in pre.iterrows():
        sig = "*" if abs(r["att"] / r["se"]) > 1.96 else " "
        print(
            f"  t={int(r['rel_time']):+3d}: ATT={r['att']:+8.2f}  "
            f"SE={r['se']:6.2f}  t-stat={r['att']/r['se']:+6.2f} {sig}"
        )

    # Joint Wald test
    t_stats = (pre["att"] / pre["se"]).values
    wald_stat = np.sum(t_stats**2)
    k = len(t_stats)
    p_joint = 1 - stats.chi2.cdf(wald_stat, k)
    print(f"\nJoint pre-trends test (Wald chi2):")
    print(f"  chi2({k}) = {wald_stat:.2f}, p-value = {p_joint:.6f}")
    print(f"  Reject H0 (parallel trends)? {'YES' if p_joint < 0.05 else 'No'}")

    print(f"\n  Mean |pre-ATT|: ${abs(pre['att']).mean():.2f}")
    print(f"  Mean |post-ATT|: ${abs(post['att']).mean():.2f}")
    if abs(post["att"]).mean() > 0:
        print(f"  Ratio pre/post: {abs(pre['att']).mean() / abs(post['att']).mean():.3f}")

# 2. Propensity diagnostics
ps = ctx.get("cs_propensity_diagnostics", [])
print(f"\n--- PROPENSITY SCORE DIAGNOSTICS ---")
print(f"Total (g,t) cells with propensity scores: {len(ps)}")
if ps:
    p_means = [d["p_hat_mean"] for d in ps]
    print(f"  Mean p-hat across cells: {np.mean(p_means):.4f}")
    print(
        f"  Range: [{min(d['p_hat_min'] for d in ps):.4f}, "
        f"{max(d['p_hat_max'] for d in ps):.4f}]"
    )
else:
    print("  NO propensity scores computed -- DR fell back to OR for all cells")

# 3. Covariate availability
panel = ctx.get("did_panel")
if panel is not None:
    covs = [
        "median_income", "median_house_value", "baseline_rent",
        "pct_bachelor", "pct_rented", "median_age", "total_population",
    ]
    print(f"\n--- COVARIATE AVAILABILITY ---")
    for c in covs:
        if c in panel.columns:
            n_valid = panel[c].notna().sum()
            pct = 100 * n_valid / len(panel)
            print(f"  {c:25s}: {n_valid:6d} / {len(panel)} ({pct:.1f}%)")
        else:
            print(f"  {c:25s}: NOT IN PANEL")

# 4. Cohort-level pre-trends
print("\n--- COHORT-LEVEL PRE-TRENDS ---")
cd = ctx.get("cs_cohort_dynamics")
if cd is not None and not cd.empty:
    for cohort in sorted(cd["cohort"].unique()):
        cohort_pre = cd[(cd["cohort"] == cohort) & (cd["rel_time"] < 0)]
        if cohort_pre.empty:
            continue
        mean_pre = cohort_pre["att"].mean()
        n_sig = ((cohort_pre["att"].abs() / cohort_pre["se"]) > 1.96).sum()
        n_total = len(cohort_pre)
        print(
            f"  Cohort {str(cohort)[:7]}: mean pre-ATT={mean_pre:+8.2f}, "
            f"{n_sig}/{n_total} significant"
        )

print("\n" + "=" * 80)
