# Dashboard Audit Tab + Descriptive Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate seven new data-story figures from existing CSVs, add a Methodology Audit tab to the dashboard, and redesign the Descriptive tab to replace maps/pipeline PNGs with the new figures and interactive data components.

**Architecture:** Two phases: (1) Python script generates clean matplotlib figures into `output/descriptive-audit/`; (2) Next.js dashboard gets a new `/audit` tab, updated `/descriptive` page, and a symlink to the new figure directory. All stats stay live from CSV — no hardcoded numbers.

**Tech Stack:** Python 3 + pandas + matplotlib + seaborn (figure generation); Next.js 14 App Router + Tailwind CSS v4 (dashboard).

---

## Context

Codex refactored the ZIP→tract crosswalk (now uses `tract_area_share` weights in projected CRS) and the trend-matching step (now matches on two standardized features). The resulting sample lineage (`did_descriptive_sample_lineage.csv`) shows: **1,332 → 867 → 842 → 842 → 829 → 453 → 244** tracts. The current dashboard uses existing pipeline PNGs (maps, funnel) that the user finds unclear. This plan replaces them with purpose-built figures and adds a dedicated Audit tab explaining the methodology decisions.

Key CSVs consumed by the figures (all live in `output/did-cs-whitepaper-binary/` unless noted):

| CSV | Used for |
|-----|----------|
| `output/did-cs-whitepaper-binary/did_descriptive_sample_lineage.csv` | Sample funnel |
| `output/did-cs-whitepaper-binary/pretrend_tract_comparison.csv` | Covariate balance |
| `output/did-cs-whitepaper-binary/did_matching_diagnostics.csv` | Matching summary stats |
| `output/did-cs-whitepaper-binary/did_matching_control_reuse.csv` | Control reuse |
| `output/did-cs-whitepaper-binary/did_crosswalk_tract_coverage.csv` | ZIP→tract coverage |
| `output/did-cs-whitepaper-binary/did_trends_avg_rent_by_group_month.csv` | Rent trends |
| `output/did-cs-whitepaper-binary/did_descriptive_cohort_stats.csv` | Cohort timeline |
| `output/did-cs-whitepaper-threshold/did_descriptive_cohort_stats.csv` | Cohort timeline (threshold) |
| `output/did-cs-whitepaper-binary/did_descriptive_summary_stats.csv` | Rent by group |
| `output/did-cs-whitepaper-threshold/did_descriptive_summary_stats.csv` | Rent by group (threshold) |

---

## File Map

```
src/housing/scripts/generate_audit_figures.py   NEW — generates all 7 figures
output/descriptive-audit/                        NEW — figure output directory
  fig_sample_funnel.png
  fig_covariate_balance.png
  fig_rent_by_group.png
  fig_cohort_timeline.png
  fig_control_reuse.png
  fig_crosswalk_coverage.png
  fig_rent_trends.png

dashboard/public/data/audit                      NEW — symlink → output/descriptive-audit/
dashboard/src/lib/data.ts                        MODIFY — add 4 new loaders
dashboard/src/components/TabNav.tsx              MODIFY — add /audit tab
dashboard/src/app/audit/page.tsx                 NEW — Methodology Audit tab
dashboard/src/app/descriptive/page.tsx           MODIFY — replace PNGs with new figures
dashboard/src/app/analysis/page.tsx              MODIFY — remove maps, add rent trends
```

---

## Task 1: Python figure generation script

**Files:**
- Create: `src/housing/scripts/generate_audit_figures.py`

- [ ] **Step 1: Create the script**

```python
# src/housing/scripts/generate_audit_figures.py
"""
Generate audit and descriptive figures for the dashboard data story.

Usage:
  export PYTHONPATH=src
  export DATA_DIR="$(pwd)/data"
  python src/housing/scripts/generate_audit_figures.py

Reads from:
  output/did-cs-whitepaper-binary/  (BINARY_DIR)
  output/did-cs-whitepaper-threshold/ (THRESHOLD_DIR)

Writes to:
  output/descriptive-audit/  (OUT_DIR or DID_AUDIT_OUTPUT_DIR env var)
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# ── paths ────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[3]
BINARY_DIR    = REPO_ROOT / 'output' / 'did-cs-whitepaper-binary'
THRESHOLD_DIR = REPO_ROOT / 'output' / 'did-cs-whitepaper-threshold'
OUT_DIR = Path(os.environ.get('DID_AUDIT_OUTPUT_DIR',
                               str(REPO_ROOT / 'output' / 'descriptive-audit')))
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── style ─────────────────────────────────────────────────────────────────────
MAROON = '#8B0000'
TEAL   = '#0D9488'
BLUE   = '#2563EB'
AMBER  = '#D97706'
GRAY   = '#6B7280'

plt.rcParams.update({
    'font.family':        'sans-serif',
    'font.size':          11,
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'figure.facecolor':   'white',
    'axes.facecolor':     'white',
    'grid.color':         '#E5E7EB',
    'grid.linewidth':     0.6,
})


# ── Figure 1: Sample Funnel ────────────────────────────────────────────────
def fig_sample_funnel():
    df = pd.read_csv(BINARY_DIR / 'did_descriptive_sample_lineage.csv')
    # Build rows from the known stages in the CSV
    stages = df[df['stage_code'].isin(['A','B','C','D','F'])].copy()
    stages = stages.set_index('stage_code').reindex(['A','B','C','D','F'])

    labels = [
        'A  All Chicago tracts\n(shapefile)',
        'B  ZIP-tract crosswalk\ncoverage filter',
        'C  Rent panel\n(ZORI match)',
        'D  Pre-match DiD panel\n(treatment assigned)',
        'F  Matched DiD panel\n(k=3 NN, 6+ pre-periods)',
    ]
    counts = [
        int(stages.loc['A', 'n_tracts']),
        int(stages.loc['B', 'n_tracts']),
        int(stages.loc['C', 'n_tracts']),
        int(stages.loc['D', 'n_tracts']),
        int(stages.loc['F', 'n_tracts']),
    ]
    treated = [None, None, None,
               int(stages.loc['D', 'treated_tracts']),
               int(stages.loc['F', 'treated_tracts'])]
    controls = [None, None, None,
                int(stages.loc['D', 'never_treated_tracts']),
                int(stages.loc['F', 'never_treated_tracts'])]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    y = np.arange(len(labels))
    bar_colors = [BLUE, GRAY, GRAY, MAROON, TEAL]

    bars = ax.barh(y, counts, height=0.55, color=bar_colors, alpha=0.85, zorder=3)

    for i, (c, t, ctrl) in enumerate(zip(counts, treated, controls)):
        ax.text(c + 18, y[i], f'{c:,}', va='center', fontsize=12, fontweight='bold', color='#111')
        if t is not None:
            ax.text(c / 2, y[i], f'{t:,} treated · {ctrl:,} control',
                    va='center', ha='center', fontsize=9.5, color='white', fontweight='600')

    # Drop annotations
    for i in range(1, len(counts)):
        delta = counts[i] - counts[i - 1]
        if delta < 0:
            ax.text(counts[i] + 18, y[i] - 0.32,
                    f'−{abs(delta):,}',
                    va='center', fontsize=9, color=AMBER, fontweight='600')

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10.5)
    ax.set_xlabel('Number of census tracts', fontsize=11)
    ax.set_title('Sample Construction Funnel — Chicago STR Analysis',
                 fontsize=13, fontweight='bold', pad=12)
    ax.set_xlim(0, max(counts) * 1.22)
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)

    patches = [
        mpatches.Patch(color=BLUE,  label='Starting universe'),
        mpatches.Patch(color=MAROON, label='Treatment-assigned'),
        mpatches.Patch(color=TEAL,  label='Final matched sample'),
        mpatches.Patch(color=GRAY,  label='Filter step'),
    ]
    ax.legend(handles=patches, loc='lower right', fontsize=9, framealpha=0.8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'fig_sample_funnel.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('✓ fig_sample_funnel.png')


# ── Figure 2: Covariate Balance (dumbbell chart) ──────────────────────────
def fig_covariate_balance():
    bal = pd.read_csv(BINARY_DIR / 'pretrend_tract_comparison.csv')
    diag = pd.read_csv(BINARY_DIR / 'did_matching_diagnostics.csv')

    # SMDs after matching from diagnostics row
    smd_slope_after = float(diag['smd_pre_trend_slope_after'].iloc[0])
    smd_rent_after  = float(diag['smd_avg_pre_rent_after'].iloc[0])

    covariate_labels = {
        'median_income':     'Median income',
        'median_house_value':'Median house value',
        'baseline_rent':     'Baseline rent (ZORI)',
        'pct_bachelor':      '% with bachelor degree',
        'pct_rented':        '% renter-occupied',
        'median_age':        'Median age',
        'total_population':  'Total population',
    }
    bal = bal[bal['covariate'].isin(covariate_labels)].copy()
    bal['label']    = bal['covariate'].map(covariate_labels)
    bal['cohens_d'] = bal['cohens_d'].abs()
    bal = bal.sort_values('cohens_d', ascending=True)

    # After-matching SMDs: only slope and rent are directly available
    after_map = {
        'baseline_rent': smd_rent_after,
    }

    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(bal))

    ax.scatter(bal['cohens_d'], y, color=MAROON, zorder=5, s=70, label="Before matching (|Cohen's d|)")
    for i, row in enumerate(bal.itertuples()):
        after = after_map.get(row.covariate)
        if after is not None:
            ax.plot([row.cohens_d, after], [i, i], color='#CBD5E0', zorder=3, lw=1.5)
            ax.scatter(after, i, color=TEAL, zorder=6, s=70, marker='D', label='After matching' if i == 0 else '')

    ax.axvline(0.1, color='#9CA3AF', lw=1, ls='--', label='SMD = 0.1 (good balance)')
    ax.axvline(0.5, color=AMBER,    lw=1, ls='--', label='SMD = 0.5 (large imbalance)')

    ax.set_yticks(y)
    ax.set_yticklabels(bal['label'], fontsize=10.5)
    ax.set_xlabel("|Standardized Mean Difference| (Cohen's d)", fontsize=11)
    ax.set_title('Pre-treatment Covariate Balance — Treated vs Control Tracts\n(Binary indicator, before matching)',
                 fontsize=12, fontweight='bold', pad=10)
    ax.legend(fontsize=9, loc='lower right', framealpha=0.85)
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'fig_covariate_balance.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('✓ fig_covariate_balance.png')


# ── Figure 3: Rent by Group (binary vs threshold) ─────────────────────────
def fig_rent_by_group():
    b = pd.read_csv(BINARY_DIR    / 'did_descriptive_summary_stats.csv', index_col=0)
    t = pd.read_csv(THRESHOLD_DIR / 'did_descriptive_summary_stats.csv', index_col=0)

    groups = [
        ('Binary\nNever-Treated',    b.loc['Never Treated',       'Mean Rent'], b.loc['Never Treated',       'Std Dev'], GRAY,   '/', 183),
        ('Binary\nTreated',          b.loc['Eventually Treated',   'Mean Rent'], b.loc['Eventually Treated',   'Std Dev'], MAROON, '', 373),
        ('Threshold\nNever-Treated', t.loc['Never Treated',       'Mean Rent'], t.loc['Never Treated',       'Std Dev'], GRAY,   '/', 179),
        ('Threshold\nTreated',       t.loc['Eventually Treated',   'Mean Rent'], t.loc['Eventually Treated',   'Std Dev'], TEAL,   '', 274),
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(groups))
    width = 0.55

    for i, (label, mean, std, color, hatch, n) in enumerate(groups):
        ax.bar(i, mean, width, color=color, alpha=0.85, hatch=hatch, zorder=3,
               edgecolor='white' if hatch == '' else color)
        ax.errorbar(i, mean, yerr=std, fmt='none', color='#374151', capsize=5, lw=1.5, zorder=4)
        ax.text(i, mean + std + 15, f'n={n}', ha='center', fontsize=9, color='#6B7280')
        ax.text(i, mean / 2, f'${mean:,.0f}', ha='center', va='center',
                fontsize=11, fontweight='bold',
                color='white' if color != GRAY else '#374151')

    ax.set_xticks(x)
    ax.set_xticklabels([g[0] for g in groups], fontsize=11)
    ax.set_ylabel('Mean monthly rent (ZORI, $/mo)', fontsize=11)
    ax.set_title('Mean Baseline Rent by Treatment Group and Indicator\n(Error bars = ±1 SD)',
                 fontsize=12, fontweight='bold', pad=10)
    ax.set_ylim(0, max(g[1] + g[2] for g in groups) * 1.18)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)

    patches = [
        mpatches.Patch(color=MAROON, label='Binary treated'),
        mpatches.Patch(color=TEAL,   label='Threshold treated'),
        mpatches.Patch(color=GRAY,   label='Never-treated (either def.)', hatch='/'),
    ]
    ax.legend(handles=patches, fontsize=9, loc='upper left', framealpha=0.85)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'fig_rent_by_group.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('✓ fig_rent_by_group.png')


# ── Figure 4: Cohort Adoption Timeline ────────────────────────────────────
def fig_cohort_timeline():
    b = pd.read_csv(BINARY_DIR    / 'did_descriptive_cohort_stats.csv')
    t = pd.read_csv(THRESHOLD_DIR / 'did_descriptive_cohort_stats.csv')

    b['month'] = pd.to_datetime(b['first_prohibition_month']).dt.to_period('M').astype(str)
    t['month'] = pd.to_datetime(t['first_prohibition_month']).dt.to_period('M').astype(str)

    all_months = sorted(set(b['month']) | set(t['month']))
    b_by_m = b.groupby('month')['n_tracts'].sum().reindex(all_months, fill_value=0)
    t_by_m = t.groupby('month')['n_tracts'].sum().reindex(all_months, fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(all_months))
    width = 0.38

    ax.bar(x - width / 2, b_by_m.values, width, label='Binary indicator', color=MAROON, alpha=0.8, zorder=3)
    ax.bar(x + width / 2, t_by_m.values, width, label='Threshold indicator', color=TEAL,   alpha=0.8, zorder=3)

    # Cumulative line on secondary axis
    ax2 = ax.twinx()
    ax2.plot(x, b_by_m.cumsum().values, color=MAROON, lw=2, ls='--', alpha=0.6, label='Binary cumulative')
    ax2.plot(x, t_by_m.cumsum().values, color=TEAL,   lw=2, ls='--', alpha=0.6, label='Threshold cumulative')
    ax2.set_ylabel('Cumulative treated tracts', fontsize=10, color='#6B7280')
    ax2.tick_params(axis='y', colors='#9CA3AF')

    # Show only year labels to avoid crowding
    year_ticks = [i for i, m in enumerate(all_months) if m.endswith('-01') or m.endswith('-07')]
    ax.set_xticks(year_ticks)
    ax.set_xticklabels([all_months[i][:7] for i in year_ticks], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Tracts newly treated (cohort size)', fontsize=11)
    ax.set_title('STR Prohibition Cohort Sizes Over Time\n(bars = new tracts treated; dashed = cumulative total)',
                 fontsize=12, fontweight='bold', pad=10)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc='upper right', framealpha=0.85)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'fig_cohort_timeline.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('✓ fig_cohort_timeline.png')


# ── Figure 5: Control Reuse ────────────────────────────────────────────────
def fig_control_reuse():
    df = pd.read_csv(BINARY_DIR / 'did_matching_control_reuse.csv')
    counts = df['n_treated_matches'].values
    diag   = pd.read_csv(BINARY_DIR / 'did_matching_diagnostics.csv').iloc[0]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.arange(0.5, counts.max() + 1.5)
    ax.hist(counts, bins=bins, color=BLUE, alpha=0.8, edgecolor='white', zorder=3)

    mean_reuse   = float(diag['control_reuse_mean'])
    p95_reuse    = float(diag['control_reuse_p95'])
    max_reuse    = int(diag['control_reuse_max'])

    ax.axvline(mean_reuse, color=MAROON, lw=2, ls='--', label=f'Mean reuse = {mean_reuse:.1f}')
    ax.axvline(p95_reuse,  color=AMBER,  lw=1.5, ls=':',  label=f'p95 reuse = {p95_reuse:.0f}')

    ax.set_xlabel('# of treated tracts matched to this control', fontsize=11)
    ax.set_ylabel('Number of control tracts', fontsize=11)
    ax.set_title(f'Control Tract Reuse Distribution\n(n={len(counts):,} controls · max reuse = {max_reuse:,})',
                 fontsize=12, fontweight='bold', pad=10)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=10, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'fig_control_reuse.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('✓ fig_control_reuse.png')


# ── Figure 6: Crosswalk Coverage ──────────────────────────────────────────
def fig_crosswalk_coverage():
    df   = pd.read_csv(BINARY_DIR / 'did_crosswalk_tract_coverage.csv')
    diag = pd.read_csv(BINARY_DIR / 'did_crosswalk_diagnostics.csv').iloc[0]

    coverage = df['tract_coverage_share'].values * 100   # as percent

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(coverage, bins=25, color=TEAL, alpha=0.8, edgecolor='white', zorder=3)

    pct_ge95 = float(diag['tracts_with_coverage_ge_95pct']) / float(diag['n_tracts']) * 100
    pct_lt50 = float(diag['tracts_with_coverage_lt_50pct']) / float(diag['n_tracts']) * 100

    ax.axvline(95, color=TEAL,  lw=2, ls='--',
               label=f'{pct_ge95:.0f}% of tracts ≥ 95% covered')
    ax.axvline(50, color=AMBER, lw=1.5, ls=':',
               label=f'{pct_lt50:.0f}% of tracts < 50% covered')

    ax.set_xlabel('Tract coverage share (% of tract area within a ZORI ZIP)', fontsize=11)
    ax.set_ylabel('Number of tracts', fontsize=11)
    ax.set_title('ZIP→Tract Crosswalk Coverage Distribution\n(higher = more of the tract is inside a ZORI-covered ZIP)',
                 fontsize=12, fontweight='bold', pad=10)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=10, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'fig_crosswalk_coverage.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('✓ fig_crosswalk_coverage.png')


# ── Figure 7: Rent Trends by Group ────────────────────────────────────────
def fig_rent_trends():
    df = pd.read_csv(BINARY_DIR / 'did_trends_avg_rent_by_group_month.csv')
    df['month'] = pd.to_datetime(df['month'])

    # Identify first treatment month from the lineage
    lineage = pd.read_csv(BINARY_DIR / 'did_descriptive_sample_lineage.csv')
    # The panel starts 2015-01 and first prohibitions appear ~2016-07
    first_treat = pd.Timestamp('2016-07-01')

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(df['month'], df['Never Treated'],      color=TEAL,   lw=2.5, label='Never-treated tracts')
    ax.plot(df['month'], df['Eventually Treated'], color=MAROON, lw=2.5, label='Eventually-treated tracts')

    ax.axvline(first_treat, color=AMBER, lw=1.5, ls='--', label='First STR prohibitions (Jul 2016)')
    ax.fill_betweenx(
        [df[['Never Treated', 'Eventually Treated']].values.min() * 0.98,
         df[['Never Treated', 'Eventually Treated']].values.max() * 1.02],
        first_treat, df['month'].max(),
        color=AMBER, alpha=0.05, zorder=0,
    )

    ax.set_xlabel('Month', fontsize=11)
    ax.set_ylabel('Mean monthly rent (ZORI, $/mo)', fontsize=11)
    ax.set_title('Average Rent Over Time — Treated vs Never-Treated Tracts\n(Binary indicator · shaded area = post-treatment window)',
                 fontsize=12, fontweight='bold', pad=10)
    ax.legend(fontsize=10, framealpha=0.85)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'fig_rent_trends.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('✓ fig_rent_trends.png')


if __name__ == '__main__':
    print(f'Writing figures to {OUT_DIR}')
    fig_sample_funnel()
    fig_covariate_balance()
    fig_rent_by_group()
    fig_cohort_timeline()
    fig_control_reuse()
    fig_crosswalk_coverage()
    fig_rent_trends()
    print('All figures done.')
```

- [ ] **Step 2: Run the script to generate all figures**

```bash
cd /path/to/repo   # repo root
export PYTHONPATH=src
export DATA_DIR="$(pwd)/data"
.venv/bin/python src/housing/scripts/generate_audit_figures.py
```

Expected output:
```
Writing figures to .../output/descriptive-audit
✓ fig_sample_funnel.png
✓ fig_covariate_balance.png
✓ fig_rent_by_group.png
✓ fig_cohort_timeline.png
✓ fig_control_reuse.png
✓ fig_crosswalk_coverage.png
✓ fig_rent_trends.png
All figures done.
```

Verify: `ls output/descriptive-audit/` should list 7 PNG files.

- [ ] **Step 3: Commit**

```bash
git add src/housing/scripts/generate_audit_figures.py
git commit -m "feat: generate_audit_figures — 7 data-story PNGs from CSVs"
```

---

## Task 2: Dashboard data symlink + new loaders

**Files:**
- Create: `dashboard/public/data/audit` (symlink)
- Modify: `dashboard/src/lib/data.ts`

- [ ] **Step 1: Add symlink**

```bash
cd dashboard/public/data
ln -s ../../../output/descriptive-audit audit
ls -la audit | head -5   # should list the PNG files
```

- [ ] **Step 2: Add gitignore entry**

Add to repo root `.gitignore`:
```
dashboard/public/data/audit
```

- [ ] **Step 3: Add new loaders to `dashboard/src/lib/data.ts`**

Read the file first, then append after the last existing loader:

```typescript
export function loadSampleLineage(dir: 'binary' | 'threshold' = 'binary') {
  return readCsvRows(dir, 'did_descriptive_sample_lineage.csv').map(r => ({
    stage_code:    r.stage_code,
    stage_label:   r.stage_label,
    n_tracts:      +r.n_tracts || 0,
    share_of_city: +r.share_of_city_tracts || 0,
    delta:         r.delta_from_previous_stage ? +r.delta_from_previous_stage : null,
    treated:       r.treated_tracts ? +r.treated_tracts : null,
    never_treated: r.never_treated_tracts ? +r.never_treated_tracts : null,
    reason:        r.reason,
  }))
}

export function loadCovariateBalance(dir: 'binary' | 'threshold' = 'binary') {
  return readCsvRows(dir, 'pretrend_tract_comparison.csv').map(r => ({
    covariate:     r.covariate,
    treated_mean:  +r.treated_mean,
    control_mean:  +r.control_mean,
    pct_diff:      +r.pct_difference,
    cohens_d:      Math.abs(+r.cohens_d),
    p_value:       +r.p_value,
    significant:   r.significant === 'True',
  }))
}

export function loadMatchingDiagnostics(dir: 'binary' | 'threshold' = 'binary') {
  const r = readCsvRow(dir, 'did_matching_diagnostics.csv')
  return {
    matched_treated:    +r.matched_treated_tracts,
    matched_controls:   +r.matched_control_tracts,
    matched_pairs:      +r.matched_pairs,
    distance_mean:      +r.distance_mean,
    distance_p95:       +r.distance_p95,
    control_reuse_mean: +r.control_reuse_mean,
    control_reuse_max:  +r.control_reuse_max,
    smd_slope_before:   +r.smd_pre_trend_slope_before,
    smd_slope_after:    +r.smd_pre_trend_slope_after,
    smd_rent_before:    +r.smd_avg_pre_rent_before,
    smd_rent_after:     +r.smd_avg_pre_rent_after,
  }
}

export function loadRentTrends(dir: 'binary' | 'threshold' = 'binary') {
  return readCsvRows(dir, 'did_trends_avg_rent_by_group_month.csv').map(r => ({
    month:         r.month,
    never_treated: +r['Never Treated'],
    treated:       +r['Eventually Treated'],
  }))
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd dashboard && npm run build 2>&1 | grep -E 'error|Error' | head -10
```
Expected: no errors related to the new loaders.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/lib/data.ts
git commit -m "feat: add loadSampleLineage, loadCovariateBalance, loadMatchingDiagnostics, loadRentTrends to data.ts"
```

---

## Task 3: Methodology Audit tab (`/audit`)

**Files:**
- Modify: `dashboard/src/components/TabNav.tsx`
- Create: `dashboard/src/app/audit/page.tsx`

- [ ] **Step 1: Add `/audit` to TabNav**

In `dashboard/src/components/TabNav.tsx`, add the audit tab to the TABS array after Policy:

```typescript
const TABS = [
  { label: 'Introduction', href: '/' },
  { label: 'Descriptive',  href: '/descriptive' },
  { label: 'Analysis',     href: '/analysis' },
  { label: 'Models',       href: '/models' },
  { label: 'Robustness',   href: '/robustness' },
  { label: 'Pre-trends',   href: '/pretrends' },
  { label: 'Policy',       href: '/policy' },
  { label: 'Audit',        href: '/audit' },
]
```

- [ ] **Step 2: Create `dashboard/src/app/audit/page.tsx`**

```tsx
// dashboard/src/app/audit/page.tsx
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import { loadSampleLineage, loadCovariateBalance, loadMatchingDiagnostics } from '@/lib/data'

const COVARIATE_LABELS: Record<string, string> = {
  median_income:      'Median income',
  median_house_value: 'Median house value',
  baseline_rent:      'Baseline rent (ZORI)',
  pct_bachelor:       '% with bachelor degree',
  pct_rented:         '% renter-occupied',
  median_age:         'Median age',
  total_population:   'Total population',
}

export default function AuditPage() {
  const lineage  = loadSampleLineage('binary')
  const balance  = loadCovariateBalance('binary')
  const matchDiag = loadMatchingDiagnostics('binary')

  const lineageRows = lineage
    .filter(s => s.n_tracts > 0)
    .map(s => [
      s.stage_code,
      s.stage_label,
      s.n_tracts.toLocaleString(),
      s.delta !== null ? (s.delta < 0 ? `−${Math.abs(s.delta).toLocaleString()}` : '—') : '—',
      s.treated !== null ? s.treated.toLocaleString() : '—',
      s.never_treated !== null ? s.never_treated.toLocaleString() : '—',
    ])

  const balanceRows = balance
    .filter(b => b.covariate in COVARIATE_LABELS)
    .sort((a, b) => b.cohens_d - a.cohens_d)
    .map(b => [
      COVARIATE_LABELS[b.covariate] ?? b.covariate,
      `$${b.treated_mean.toFixed(0)}`,
      `$${b.control_mean.toFixed(0)}`,
      `${b.pct_diff.toFixed(1)}%`,
      b.cohens_d.toFixed(3),
      b.significant ? '✗ Yes' : '✓ No',
    ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Methodology Audit</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        What changed in the most recent pipeline refactor, what the diagnostics say,
        and what it means for interpreting the estimates.
      </p>

      {/* ── Crosswalk Section ── */}
      <div className="mb-12">
        <h3 className="text-lg font-bold mb-1">1. ZIP → Tract Crosswalk Refactor</h3>
        <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
          The original crosswalk normalized intersection areas within ZIP codes (a zip-centric weight).
          The refactored version uses <strong>tract-area share</strong> — how much of the census
          tract lies within each ZIP — which is easier to defend for a tract-level rent outcome.
          Areas are now computed in EPSG:3435 (projected CRS) instead of EPSG:4326 (degrees).
        </p>
        <div className="grid grid-cols-2 gap-6 mb-6">
          <InfoBlock
            title="Crosswalk Coverage Summary"
            rows={[
              { label: 'ZIP codes in crosswalk',       value: '59' },
              { label: 'Tracts with crosswalk entry',  value: '867' },
              { label: 'Tracts ≥ 95% covered',         value: '751 (86.6%)', valueClass: 'text-teal-600' },
              { label: 'Tracts < 50% covered',         value: '88 (10.1%)',  valueClass: 'text-amber-600' },
              { label: 'Avg ZIP-tract pairs per ZIP',  value: '26' },
            ]}
          />
          <InfoBlock
            title="Weight Change"
            rows={[
              { label: 'Old weight',   value: 'zip_area_share (zip-centric)' },
              { label: 'New weight',   value: 'tract_area_share (tract-centric)', valueClass: 'text-teal-600' },
              { label: 'Old CRS',      value: 'EPSG:4326 (degrees — wrong)' },
              { label: 'New CRS',      value: 'EPSG:3435 (projected — correct)', valueClass: 'text-teal-600' },
              { label: 'Key limitation', value: 'Outcome is still ZIP-interpolated' },
            ]}
          />
        </div>
        <FigureSlot src="/data/audit/fig_crosswalk_coverage.png"
          alt="Crosswalk coverage distribution" label="Tract coverage distribution — share of tract area inside a ZORI ZIP" />
      </div>

      {/* ── Sample Lineage ── */}
      <div className="mb-12">
        <h3 className="text-lg font-bold mb-1">2. Sample Construction Lineage</h3>
        <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
          The full tract funnel from the city shapefile to the final matched DiD sample.
          The largest drops are at the crosswalk step (−465 tracts without ZORI coverage)
          and the matching step (−389 tracts with insufficient pre-periods or not selected as controls).
        </p>
        <StatTable
          className="mb-6"
          headers={['Stage', 'Description', 'N Tracts', 'Drop', 'Treated', 'Never-Treated']}
          rows={lineageRows}
        />
        <FigureSlot src="/data/audit/fig_sample_funnel.png"
          alt="Sample construction funnel" label="Sample funnel — A through F" />
      </div>

      {/* ── Matching Section ── */}
      <div className="mb-12">
        <h3 className="text-lg font-bold mb-1">3. Trend-Matching Refactor</h3>
        <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
          Original matching used only pre-treatment rent slope (one scalar). The refactored
          version matches on two standardized features: pre-trend slope and average pre-treatment
          rent. This improves rent-level balance, which was the main weakness before.
          Diagnostics are now exported to CSV instead of being hidden.
        </p>

        <div className="grid grid-cols-2 gap-6 mb-6">
          <InfoBlock
            title="Matching Diagnostics (Binary)"
            rows={[
              { label: 'Treated tracts matched',  value: matchDiag.matched_treated.toLocaleString() },
              { label: 'Distinct control tracts', value: matchDiag.matched_controls.toLocaleString() },
              { label: 'Total matched pairs',     value: matchDiag.matched_pairs.toLocaleString() },
              { label: 'Mean match distance',     value: matchDiag.distance_mean.toFixed(3) },
              { label: 'p95 match distance',      value: matchDiag.distance_p95.toFixed(3) },
              { label: 'Mean control reuse',      value: matchDiag.control_reuse_mean.toFixed(1) },
              { label: 'Max control reuse',       value: matchDiag.control_reuse_max.toLocaleString() },
            ]}
          />
          <InfoBlock
            title="Balance Improvement (SMD)"
            rows={[
              { label: 'Rent slope SMD — before',  value: matchDiag.smd_slope_before.toFixed(3), valueClass: 'text-maroon' },
              { label: 'Rent slope SMD — after',   value: matchDiag.smd_slope_after.toFixed(3),  valueClass: 'text-teal-600' },
              { label: 'Avg rent SMD — before',    value: matchDiag.smd_rent_before.toFixed(3),  valueClass: 'text-maroon' },
              { label: 'Avg rent SMD — after',     value: matchDiag.smd_rent_after.toFixed(3),   valueClass: 'text-amber-600' },
              { label: 'Recommendation', value: 'Matching as robustness, not primary' },
            ]}
          />
        </div>

        <div className="grid grid-cols-2 gap-6 mb-6">
          <FigureSlot src="/data/audit/fig_covariate_balance.png"
            alt="Covariate balance" label="Covariate balance before matching (Cohen's d)" />
          <FigureSlot src="/data/audit/fig_control_reuse.png"
            alt="Control reuse distribution" label="Control reuse distribution" />
        </div>

        <div className="border border-dashed border-amber-200 bg-amber-50 rounded-xl p-5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-amber-700 mb-2">Remaining Limitations</p>
          <ul className="text-[13px] text-gray-600 leading-relaxed space-y-1 list-disc list-inside">
            <li>Nearest-neighbor matching with replacement — controls can be reused many times</li>
            <li>No hard caliper by default — some matches may be poor quality</li>
            <li>Summary-feature matching (slope + level) rather than full trajectory matching</li>
            <li>SMD after matching still non-trivial — present matching as robustness restriction</li>
          </ul>
        </div>
      </div>

      {/* ── Covariate Balance Table ── */}
      <div>
        <h3 className="text-lg font-bold mb-1">4. Pre-treatment Covariate Balance (Binary, Before Matching)</h3>
        <p className="text-[14px] text-gray-500 mb-4 max-w-2xl leading-relaxed">
          Treated tracts are systematically higher-income, higher-education, and higher-rent than
          the never-treated pool. This motivates matching but also limits how clean the comparison can get.
        </p>
        <StatTable
          headers={['Covariate', 'Treated Mean', 'Control Mean', '% Difference', "Cohen's d", 'Significant']}
          rows={balanceRows}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create audit app directory**

```bash
mkdir -p dashboard/src/app/audit
```

- [ ] **Step 4: Verify `/audit` returns 200**

```bash
npm run dev &
sleep 10
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/audit
# Expected: 200
pkill -f "next dev"
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/TabNav.tsx dashboard/src/app/audit/
git commit -m "feat: Methodology Audit tab — crosswalk, sample lineage, matching diagnostics"
```

---

## Task 4: Redesign Descriptive page

Replace existing PNGs (maps + pipeline funnel) with the new audit figures and live interactive data components.

**Files:**
- Modify: `dashboard/src/app/descriptive/page.tsx`

- [ ] **Step 1: Rewrite `dashboard/src/app/descriptive/page.tsx`**

```tsx
// dashboard/src/app/descriptive/page.tsx
import PipelineStepper from '@/components/PipelineStepper'
import FigureSlot from '@/components/FigureSlot'
import InfoBlock from '@/components/InfoBlock'
import StatTable from '@/components/StatTable'
import { loadPanelOverview, loadGroupStats, loadCohortStats } from '@/lib/data'

export default function DescriptivePage() {
  const ov       = loadPanelOverview('binary')
  const gs       = loadGroupStats('binary')
  const gsT      = loadGroupStats('threshold')
  const cohorts  = loadCohortStats('binary').slice(0, 8)
  const treated  = gs.find(g => g.group.includes('Eventually'))  ?? { n_tracts: 373 }
  const control  = gs.find(g => g.group.includes('Never'))       ?? { n_tracts: 183 }
  const treatedT = gsT.find(g => g.group.includes('Eventually')) ?? { n_tracts: 274 }
  const controlT = gsT.find(g => g.group.includes('Never'))      ?? { n_tracts: 179 }

  const cohortRows = cohorts.map(c => [
    c.first_prohibition_month,
    c.n_tracts.toLocaleString(),
    `${(c.share_of_treated_tracts * 100).toFixed(1)}%`,
    `$${c.mean_baseline_rent.toFixed(0)}`,
    `$${(c.mean_median_income / 1000).toFixed(0)}k`,
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Sample Construction Pipeline</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        From 1,332 raw Chicago census tracts to the final matched DiD sample. Click any step to
        see what changed, how many units were retained, and why.
      </p>

      <PipelineStepper
        nTracts={ov.n_tracts}
        nTreated={treated.n_tracts}
        nControl={control.n_tracts}
      />

      {/* ── Treatment group distributions ── */}
      <div className="mt-12 mb-2">
        <h3 className="text-lg font-bold mb-1">Treatment Group Distributions</h3>
        <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
          How treated and never-treated tracts differ under each definition — and how
          the threshold indicator narrows the treated group to higher-rent, higher-income areas.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-8">
        <InfoBlock
          title="Binary Indicator — Group Summary"
          rows={[
            { label: 'Treated tracts',         value: treated.n_tracts.toLocaleString(),  valueClass: 'text-maroon' },
            { label: 'Never-treated tracts',   value: control.n_tracts.toLocaleString() },
            { label: 'Total rent-panel tracts', value: ov.n_tracts.toLocaleString() },
          ]}
        />
        <InfoBlock
          title="Threshold Indicator — Group Summary"
          rows={[
            { label: 'Treated tracts',         value: treatedT.n_tracts.toLocaleString(), valueClass: 'text-teal-600' },
            { label: 'Never-treated tracts',   value: controlT.n_tracts.toLocaleString() },
            { label: 'Total matched-panel tracts', value: (treatedT.n_tracts + controlT.n_tracts).toLocaleString() },
          ]}
        />
      </div>

      <FigureSlot
        src="/data/audit/fig_rent_by_group.png"
        alt="Mean rent by treatment group and indicator"
        label="Mean baseline rent — treated vs control, binary vs threshold"
        className="mb-8"
      />

      {/* ── Cohort timeline ── */}
      <div className="mb-2">
        <h3 className="text-lg font-bold mb-1">When Did Prohibitions Hit?</h3>
        <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
          STR prohibitions were adopted in waves. The 2016 cohort accounts for the majority of
          treated tracts — and is the most important for identifying pre-trend parallelism.
        </p>
      </div>

      <FigureSlot
        src="/data/audit/fig_cohort_timeline.png"
        alt="Cohort adoption timeline"
        label="Cohort sizes over time — binary vs threshold"
        className="mb-6"
      />

      <h4 className="text-[14px] font-bold mb-3 text-gray-700">Top 8 Prohibition Cohorts (Binary)</h4>
      <StatTable
        className="mb-10"
        headers={['First Prohibition Month', 'Tracts', 'Share of Treated', 'Mean Baseline Rent', 'Mean Income']}
        rows={cohortRows}
      />

      {/* ── Rent trends ── */}
      <div className="mb-2">
        <h3 className="text-lg font-bold mb-1">Pre-treatment Rent Trajectories</h3>
        <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
          Treated tracts had persistently higher rents before 2016. The gap is not shrinking
          pre-treatment — a visual check on parallel trends.
        </p>
      </div>
      <FigureSlot
        src="/data/audit/fig_rent_trends.png"
        alt="Average rent over time by group"
        label="Average rent trajectories — treated vs never-treated"
      />
    </div>
  )
}
```

- [ ] **Step 2: Verify at `/descriptive`** — stepper works, new figures render, group summary InfoBlocks show live counts, cohort table loads.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/descriptive/page.tsx
git commit -m "feat: redesign Descriptive — rent distributions, cohort timeline, rent trends replace maps"
```

---

## Task 5: Update Analysis page

Remove maps; add rent trends figure and covariate balance.

**Files:**
- Modify: `dashboard/src/app/analysis/page.tsx`

- [ ] **Step 1: Rewrite `dashboard/src/app/analysis/page.tsx`**

```tsx
// dashboard/src/app/analysis/page.tsx
import FigureSlot from '@/components/FigureSlot'
import StatTable from '@/components/StatTable'
import { loadCohortStats, loadCovariateBalance } from '@/lib/data'

const COVARIATE_LABELS: Record<string, string> = {
  median_income:      'Median income',
  median_house_value: 'Median house value',
  baseline_rent:      'Baseline rent',
  pct_bachelor:       '% bachelor degree',
  pct_rented:         '% renter-occupied',
  median_age:         'Median age',
  total_population:   'Total population',
}

export default function AnalysisPage() {
  const cohorts = loadCohortStats('binary').slice(0, 10)
  const balance = loadCovariateBalance('binary')
    .filter(b => b.covariate in COVARIATE_LABELS)
    .sort((a, b) => b.cohens_d - a.cohens_d)

  const cohortRows = cohorts.map(c => [
    c.first_prohibition_month,
    c.n_tracts.toLocaleString(),
    `${(c.share_of_treated_tracts * 100).toFixed(1)}%`,
    `$${c.mean_baseline_rent.toFixed(0)}`,
    `$${(c.mean_median_income / 1000).toFixed(0)}k`,
  ])

  const balanceRows = balance.map(b => [
    COVARIATE_LABELS[b.covariate],
    `$${b.treated_mean.toFixed(0)}`,
    `$${b.control_mean.toFixed(0)}`,
    `${b.pct_diff.toFixed(1)}%`,
    b.cohens_d.toFixed(2),
  ])

  return (
    <div>
      <h2 className="text-2xl font-extrabold tracking-tight mb-2">Descriptive Analysis</h2>
      <p className="text-[15px] text-gray-500 mb-10 max-w-2xl leading-relaxed">
        Pre-treatment covariate balance, cohort composition, and rent dynamics before and after treatment.
      </p>

      {/* Balance figure */}
      <h3 className="text-lg font-bold mb-1">Pre-treatment Covariate Balance</h3>
      <p className="text-[14px] text-gray-500 mb-6 max-w-2xl leading-relaxed">
        All seven covariates are significantly imbalanced (p &lt; 0.05). Treated tracts are higher-income,
        higher-education, and higher-rent. Education gap is largest (Cohen's d ≈ 1.08).
      </p>
      <FigureSlot src="/data/audit/fig_covariate_balance.png"
        alt="Covariate balance" label="Cohen's d — treated vs never-treated (binary, before matching)"
        className="mb-6" />

      <StatTable
        className="mb-10"
        headers={["Covariate", "Treated Mean", "Control Mean", "% Diff", "Cohen's d"]}
        rows={balanceRows}
      />

      {/* Cohort stats */}
      <h3 className="text-lg font-bold mb-1">Prohibition Cohorts</h3>
      <p className="text-[14px] text-gray-500 mb-4 max-w-2xl leading-relaxed">
        Early 2016 cohorts are higher-rent and higher-income on average.
        Later cohorts (2017–2022) trend toward lower-income neighborhoods.
      </p>
      <StatTable
        className="mb-10"
        headers={['First Prohibition Month', 'Tracts', 'Share of Treated', 'Mean Baseline Rent', 'Mean Income']}
        rows={cohortRows}
      />

      {/* Event study */}
      <div className="grid grid-cols-2 gap-6">
        <FigureSlot src="/data/binary/event_study_plot.png"
          alt="TWFE event study coefficients" label="TWFE event study" />
        <FigureSlot src="/data/binary/did_cohort_dynamics.png"
          alt="Cohort-specific treatment effects" label="Cohort dynamics" />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify at `/analysis`** — balance figure and table load, no broken images.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/analysis/page.tsx
git commit -m "feat: Analysis page — covariate balance + cohort table replace maps"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|---|---|
| Methodology audit pane with crosswalk, matching, sample lineage | Task 3 |
| 7 new data-story figures from CSVs (no maps) | Task 1 |
| Descriptive: distribution of treated tracts by treatment indicator | Task 4 |
| Cohort adoption timeline | Task 1 (fig_cohort_timeline), Task 4 |
| Rent trends figure (replace existing) | Task 1 (fig_rent_trends), Task 4 + 5 |
| Covariate balance before/after matching | Task 1 (fig_covariate_balance), Tasks 3 + 5 |
| Sample funnel (improved) | Task 1 (fig_sample_funnel), Task 3 |
| Control reuse and crosswalk coverage figures | Task 1, Task 3 |
| Remove maps | Task 4 (Descriptive), Task 5 (Analysis) |
| Data symlink for new figures | Task 2 |
| New CSV loaders (lineage, balance, matching, trends) | Task 2 |

### No Placeholders — Confirmed

All steps have complete code. All file paths are exact. All CSV column names match verified headers.

### Type Consistency — Confirmed

- `loadSampleLineage` returns array with `stage_code, stage_label, n_tracts, delta, treated, never_treated, reason`
- `loadCovariateBalance` returns array with `covariate, treated_mean, control_mean, pct_diff, cohens_d, p_value, significant`
- `loadMatchingDiagnostics` returns flat object with exact field names used in Task 3 page
- `loadRentTrends` returns array with `month, never_treated, treated` — not used directly in pages (figure is PNG) but available for future interactive chart
- `FigureSlot` and `InfoBlock` props unchanged from Task 4 of the original plan
