"""Plot and tabulate robustness sweep results (raw vs residualized CS ATTs).

Reads ``docs/robustness/*_sweep_summary.csv`` and writes figures + LaTeX-ready tables
under ``docs/robustness/figures/`` and ``docs/robustness/tables/``.

Usage:
  export PYTHONPATH=src
  python src/housing/scripts/plot_robustness_sweeps.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs" / "robustness"
FIG_DIR = DOCS / "figures"
TAB_DIR = DOCS / "tables"

ATT_COLS = [
    ("cs_full_panel_att", "cs_full_panel_se", "Full-panel CS (preferred)"),
    ("cs_matched_att", "cs_matched_se", "Matched-sample CS"),
    ("cs_with_controls_att", "cs_with_controls_se", "Residualized CS w/ controls"),
]


def _safe_int(df: pd.DataFrame, value: str, col: str) -> str:
    sub = df[df["value"].astype(str) == value]
    if sub.empty or col not in sub.columns or pd.isna(sub[col].iloc[0]):
        return "n/a"
    return str(int(sub[col].iloc[0]))


def _load_csv(name: str) -> pd.DataFrame:
    path = DOCS / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path} — run run_robustness_sweeps.py first")
    sweep_df = pd.read_csv(path)
    if "error" in sweep_df.columns:
        bad = sweep_df[sweep_df["error"].notna()]
        if not bad.empty:
            logger.warning("Rows with errors:\n%s", bad[["value", "error"]])
    return sweep_df


def _plot_sweep(
    df: pd.DataFrame,
    *,
    x_col: str,
    x_label: str,
    title: str,
    out_name: str,
) -> None:
    """Three-panel ATT lines: full-panel, matched, residualized."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharex=True)
    x = pd.to_numeric(df["value"], errors="coerce")

    for ax, (att_col, se_col, subtitle) in zip(axes, ATT_COLS, strict=True):
        y = pd.to_numeric(df[att_col], errors="coerce")
        se = pd.to_numeric(
            df.get(se_col, pd.Series([float("nan")] * len(df))), errors="coerce"
        )
        ax.errorbar(
            x, y, yerr=1.96 * se, fmt="o-", capsize=4, color="#800000", linewidth=1.5
        )
        ax.axhline(0.0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_title(subtitle, fontsize=11)
        ax.set_ylabel("ATT ($/month, rent index)")
        ax.grid(alpha=0.25)

    for ax in axes:
        ax.set_xlabel(x_label)

    fig.suptitle(title, fontsize=13, y=1.02)
    fig.tight_layout()
    out = FIG_DIR / out_name
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Wrote %s", out)


def _plot_sample_diagnostics(
    df: pd.DataFrame, *, x_col: str, x_label: str, out_name: str
) -> None:
    """Matched tract counts and control reuse vs design parameter."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    x = pd.to_numeric(df["value"], errors="coerce")

    axes[0].plot(
        x, df["n_matched_treated_tracts"], "o-", color="#800000", label="Treated"
    )
    axes[0].plot(
        x, df["n_matched_control_tracts"], "s-", color="#1f3a5f", label="Control"
    )
    axes[0].set_xlabel(x_label)
    axes[0].set_ylabel("Matched tracts")
    axes[0].set_title("Matched sample size")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    if "max_control_reuse" in df.columns:
        axes[1].bar(x.astype(str), df["max_control_reuse"], color="#E36414", alpha=0.85)
        axes[1].set_xlabel(x_label)
        axes[1].set_ylabel("Max times a control tract is reused")
        axes[1].set_title("Control reuse")
    else:
        axes[1].set_visible(False)

    fig.tight_layout()
    out = FIG_DIR / out_name
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Wrote %s", out)


def _write_comparison_table(df: pd.DataFrame, *, out_name: str) -> None:
    """Wide table: parameter × three ATT columns for paper appendix."""
    cols = [
        "value",
        "n_matched_treated_tracts",
        "n_matched_control_tracts",
        "max_control_reuse",
    ]
    for att_col, se_col, _label in ATT_COLS:
        cols.extend([att_col, se_col])
    if "n_ever_treated_tracts" in df.columns:
        cols.append("n_ever_treated_tracts")

    sub = df[[c for c in cols if c in df.columns]].copy()
    sub = sub.rename(
        columns={
            "value": "parameter_value",
            "cs_full_panel_att": "att_full_panel",
            "cs_full_panel_se": "se_full_panel",
            "cs_matched_att": "att_matched",
            "cs_matched_se": "se_matched",
            "cs_with_controls_att": "att_residualized",
            "cs_with_controls_se": "se_residualized",
        }
    )
    TAB_DIR.mkdir(parents=True, exist_ok=True)
    path = TAB_DIR / out_name
    sub.to_csv(path, index=False)
    logger.info("Wrote %s", path)


def _write_findings_md(k_df: pd.DataFrame, p_df: pd.DataFrame) -> None:
    """Short narrative stub with numeric ranges for reviewers."""
    lines = [
        "# Robustness sweep findings (auto-generated)\n",
        "Compare **full-panel** and **matched** CS ATTs (rent index, $/month) with "
        "**residualized CS w/ controls** (different scale — do not compare levels directly).\n",
        "## k-neighbors (threshold treatment, default percentile)\n",
    ]
    if not k_df.empty:
        fp = k_df["cs_full_panel_att"].astype(float)
        mt = k_df["cs_matched_att"].astype(float)
        rs = k_df["cs_with_controls_att"].astype(float)
        lines.append(
            f"- Full-panel ATT range: ${fp.min():.2f} – ${fp.max():.2f} across k={k_df['value'].tolist()}\n"
        )
        lines.append(
            f"- Matched ATT range: ${mt.min():.2f} – ${mt.max():.2f}; "
            f"residualized range: ${rs.min():.2f} – ${rs.max():.2f}\n"
        )
        lines.append(
            f"- Matched treated tracts at k=3: "
            f"{_safe_int(k_df, '3', 'n_matched_treated_tracts')}\n"
        )
    lines.extend(
        [
            "\n## Threshold percentile (k=3 matching)\n",
        ]
    )
    if not p_df.empty:
        fp = p_df["cs_full_panel_att"].astype(float)
        lines.append(
            f"- Full-panel ATT range across percentiles: ${fp.min():.2f} – ${fp.max():.2f}\n"
        )
        if "n_ever_treated_tracts" in p_df.columns:
            lines.append(
                f"- Ever-treated tracts: {int(p_df['n_ever_treated_tracts'].min())} "
                f"(min pct) to {int(p_df['n_ever_treated_tracts'].max())} (max pct)\n"
            )
    lines.extend(
        [
            "\n## Figures\n",
            "- `figures/k_neighbors_att_by_spec.png` — ATT vs k for three estimators\n",
            "- `figures/threshold_percentile_att_by_spec.png` — ATT vs percentile\n",
            "- `figures/k_neighbors_sample_diagnostics.png` — sample size & control reuse\n",
            "\nSee [`PREFERRED_SPEC.md`](../PREFERRED_SPEC.md) for locked defaults.\n",
        ]
    )
    (DOCS / "ROBUSTNESS_FINDINGS.md").write_text("".join(lines), encoding="utf-8")
    logger.info("Wrote %s", DOCS / "ROBUSTNESS_FINDINGS.md")


def main() -> None:
    """Load sweep CSVs and emit figures, tables, and findings markdown."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TAB_DIR.mkdir(parents=True, exist_ok=True)

    k_df = _load_csv("k_neighbors_sweep_summary.csv")
    p_df = _load_csv("threshold_percentile_sweep_summary.csv")

    _plot_sweep(
        k_df,
        x_col="value",
        x_label="k neighbors per treated tract",
        title="Robustness: matching depth (k)",
        out_name="k_neighbors_att_by_spec.png",
    )
    _plot_sweep(
        p_df,
        x_col="value",
        x_label="Treatment threshold percentile",
        title="Robustness: prohibition-intensity threshold",
        out_name="threshold_percentile_att_by_spec.png",
    )
    _plot_sample_diagnostics(
        k_df,
        x_col="value",
        x_label="k",
        out_name="k_neighbors_sample_diagnostics.png",
    )
    _write_comparison_table(k_df, out_name="tab_k_neighbors_sweep.csv")
    _write_comparison_table(p_df, out_name="tab_threshold_percentile_sweep.csv")
    _write_findings_md(k_df, p_df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
