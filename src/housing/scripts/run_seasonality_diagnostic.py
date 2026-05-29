r"""Compare matched-sample CS on raw vs calendar-month demeaned rents.

Usage:
  export PYTHONPATH=src
  python src/housing/scripts/run_seasonality_diagnostic.py \\
    --panel-csv output/did-cs-whitepaper-threshold/did_panel_data.csv
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from housing.components.analyzers.callaway_santanna import CallawaySantAnnaAnalyzer
from housing.components.analyzers.callaway_santanna_pretrend_test import (
    compute_pre_trend_joint_test_from_cs_event_study,
)
from housing.components.analyzers.callaway_santanna_summary import (
    CallawaySantAnnaSummaryAnalyzer,
)
from housing.components.processors.seasonal_demean import demean_by_calendar_month
from housing.components.processors.trend_matching import TrendMatchingProcessor
from housing.components.utils import setup_figure_and_save
from housing.did_spec import (
    DID_CS_ANTICIPATION,
    DID_CS_COMPARISON_GROUP,
    DID_CS_MIN_COHORT_SIZE,
    DID_TREND_MATCH_MIN_PRE_PERIODS,
    resolve_trend_match_caliper,
    resolve_trend_match_k_neighbors,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROBUSTNESS = REPO_ROOT / "docs" / "robustness"
COHORT_PLOT_PRE_MONTHS = 12
COHORT_PLOT_POST_MONTHS = 24


def _load_panel(path: Path) -> pd.DataFrame:
    panel = pd.read_csv(path, low_memory=False)
    panel["month"] = pd.to_datetime(panel["month"])
    panel["tract_geoid"] = panel["tract_geoid"].astype(str)
    return panel


def _run_branch(
    panel: pd.DataFrame,
    *,
    label: str,
    demean: bool,
) -> dict[str, Any]:
    work = panel.copy()
    if demean:
        work = demean_by_calendar_month(work)

    matcher = TrendMatchingProcessor(
        k_neighbors=resolve_trend_match_k_neighbors(),
        min_pre_periods=DID_TREND_MATCH_MIN_PRE_PERIODS,
        caliper=resolve_trend_match_caliper(),
    )
    matched = matcher.execute({"did_panel": work})["did_panel"]

    cs = CallawaySantAnnaAnalyzer(
        comparison_group=DID_CS_COMPARISON_GROUP,
        anticipation=DID_CS_ANTICIPATION,
        min_cohort_size=DID_CS_MIN_COHORT_SIZE,
    )
    cs_out = cs.execute({"did_panel": matched})

    event_study = cs_out.get("cs_event_study")
    pre_test = compute_pre_trend_joint_test_from_cs_event_study(event_study)
    summary = pre_test["summary"]

    sig_analyzer = CallawaySantAnnaSummaryAnalyzer()
    sig_counts = sig_analyzer._compute_pretrend_significance(cs_out)

    pre = event_study[
        (event_study["rel_time"] >= -COHORT_PLOT_PRE_MONTHS)
        & (event_study["rel_time"] <= -1)
    ]
    max_abs_pre = float(pre["att"].abs().max()) if not pre.empty else float("nan")

    cohort_2019 = None
    if not sig_counts.empty:
        for _, row in sig_counts.iterrows():
            if "2019-10" in str(row["cohort"]):
                cohort_2019 = int(row["n_significant_pre_coefs"])
                break

    overall = cs_out.get("cs_overall_att", {})
    return {
        "branch": label,
        "demeaned": demean,
        "matched_att": overall.get("att"),
        "matched_se": overall.get("se"),
        "pretrend_wald": summary.get("wald_statistic"),
        "pretrend_p": summary.get("p_value"),
        "max_abs_pre_coef": max_abs_pre,
        "cohort_2019_10_sig_pre": cohort_2019,
        "cs_cohort_dynamics": cs_out.get("cs_cohort_dynamics"),
        "cs_event_study": event_study,
    }


def _plot_cohort_comparison(
    raw_dyn: pd.DataFrame,
    demean_dyn: pd.DataFrame,
    out_path: Path,
    *,
    panels_per_page: int = 6,
) -> None:
    """Cohort panels for raw vs month-demeaned; paginated PNGs when many cohorts."""
    cohorts = sorted(
        set(raw_dyn["cohort"].astype(str).unique())
        | set(demean_dyn["cohort"].astype(str).unique())
    )
    if not cohorts:
        return

    n_cols = 2
    n_pages = (len(cohorts) + panels_per_page - 1) // panels_per_page
    written: list[Path] = []

    for page in range(n_pages):
        page_cohorts = cohorts[page * panels_per_page : (page + 1) * panels_per_page]
        n_panels = len(page_cohorts)
        n_rows = (n_panels + n_cols - 1) // n_cols
        fig, axes = plt.subplots(
            n_rows, n_cols, figsize=(12, 4.5 * n_rows), squeeze=False
        )
        axes_flat = axes.flatten()

        for idx, cohort in enumerate(page_cohorts):
            ax = axes_flat[idx]
            for dyn, color, lbl in (
                (raw_dyn, "#34495e", "Raw"),
                (demean_dyn, "#c0392b", "Month demeaned"),
            ):
                sub = dyn[dyn["cohort"].astype(str) == cohort].sort_values("rel_time")
                if sub.empty:
                    continue
                w = sub[
                    (sub["rel_time"] >= -COHORT_PLOT_PRE_MONTHS)
                    & (sub["rel_time"] <= COHORT_PLOT_POST_MONTHS)
                ]
                ax.plot(
                    w["rel_time"],
                    w["att"],
                    color=color,
                    marker="o",
                    markersize=4,
                    linewidth=1.3,
                    label=lbl,
                )
            ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
            ax.axvline(0, color="#800000", linestyle=":", linewidth=1)
            title = str(cohort)[:10]
            if "2019-10" in title:
                title = f"{title} (highlight)"
            ax.set_title(title, fontsize=12)
            ax.set_xlabel("Months since treatment", fontsize=11)
            ax.set_ylabel("ATT ($/mo.)", fontsize=11)
            ax.legend(fontsize=10)
            ax.tick_params(labelsize=10)
            ax.grid(True, alpha=0.25)

        for idx in range(n_panels, len(axes_flat)):
            axes_flat[idx].axis("off")

        page_note = f" (page {page + 1}/{n_pages})" if n_pages > 1 else ""
        fig.suptitle(
            "Cohort dynamics: raw vs calendar-month demeaned rents (matched CS)"
            + page_note,
            fontsize=14,
        )
        plt.tight_layout(rect=[0, 0, 1, 0.97])

        if n_pages > 1:
            page_path = out_path.with_name(
                f"{out_path.stem}_p{page + 1}{out_path.suffix}"
            )
        else:
            page_path = out_path
        setup_figure_and_save(fig, page_path, title=None, logger=logger)
        written.append(page_path)

    if len(written) > 1:
        out_path.write_bytes(written[0].read_bytes())


def _write_seasonality_latex(comparison: pd.DataFrame, out_path: Path) -> None:
    """Emit a small booktabs table for the whitepaper appendix."""
    lines = [
        "% Auto-generated",
        "\\begin{tabular}{@{} l r r r r @{}}",
        "\\toprule",
        "Spec & ATT (\\$/mo.) & SE & Pre-trend $p$ & 2019-10 pre-viol. \\\\",
        "\\midrule",
    ]
    for _, row in comparison.iterrows():
        lbl = "Raw" if row["branch"] == "raw" else "Month demeaned"
        att = row.get("matched_att")
        se = row.get("matched_se")
        att_s = f"{float(att):,.1f}".replace(",", "{,}") if pd.notna(att) else "---"
        se_s = f"({float(se):,.2f})".replace(",", "{,}") if pd.notna(se) else "---"
        pval = row.get("pretrend_p")
        p_s = f"{float(pval):.3f}" if pd.notna(pval) else "---"
        c19 = row.get("cohort_2019_10_sig_pre")
        c_s = str(int(c19)) if pd.notna(c19) else "---"
        lines.append(f"{lbl} & {att_s} & {se_s} & {p_s} & {c_s} \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}"])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_memo(
    comparison: pd.DataFrame,
    out_path: Path,
    *,
    adopt_threshold_att_delta: float = 3.0,
) -> None:
    """Write adopt/reject recommendation for calendar-month FE."""
    raw = comparison[comparison["branch"] == "raw"].iloc[0]
    dem = comparison[comparison["branch"] == "month_demeaned"].iloc[0]

    att_delta = abs(float(dem["matched_att"]) - float(raw["matched_att"]))
    sig_raw = raw.get("cohort_2019_10_sig_pre")
    sig_dem = dem.get("cohort_2019_10_sig_pre")

    adopt_headline = (
        att_delta <= adopt_threshold_att_delta
        and pd.notna(sig_dem)
        and pd.notna(sig_raw)
        and sig_dem < sig_raw
    )

    lines = [
        "# Calendar-month fixed effects diagnostic",
        "",
        "Comparison of matched-sample Callaway--Sant'Anna on **raw** ZORI levels vs "
        "**panel-wide month-of-year demeaned** rents (same matching, $k=3$, five-feature).",
        "",
        "## Results",
        "",
        "| branch | matched_att | matched_se | pretrend_p | cohort_2019_10_sig_pre |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['branch']} | {row.get('matched_att', '')} | "
            f"{row.get('matched_se', '')} | {row.get('pretrend_p', '')} | "
            f"{row.get('cohort_2019_10_sig_pre', '')} |"
        )
    lines.extend(
        [
            "",
            f"- Pooled matched ATT change (abs): **${att_delta:.2f}/mo**",
            f"- 2019-10 cohort pre-violations (sig of 11): raw={sig_raw}, demeaned={sig_dem}",
            f"- Joint pre-trend $p$: raw={raw.get('pretrend_p'):.4g}, "
            f"demeaned={dem.get('pretrend_p'):.4g}",
            "",
            "## Recommendation",
            "",
        ]
    )
    if adopt_headline:
        lines.append(
            "**Appendix sensitivity (optional headline):** Month demeaning reduces "
            "2019-10 pre-trend violations without large ATT movement. Do **not** "
            "replace the primary rent-level estimand without reviewer sign-off."
        )
    else:
        lines.append(
            "**Do not adopt for headline spec:** Either pooled ATT moves materially "
            f"(>${adopt_threshold_att_delta:.0f}/mo) or 2019-10 pre-trends do not "
            "improve clearly. Report as appendix diagnostic only."
        )
    lines.extend(
        [
            "",
            "Figures: `docs/robustness/figures/did_cohort_dynamics_seasonality_compare.png`",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """CLI entrypoint: raw vs calendar-month demeaned matched CS diagnostic."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Raw vs calendar-month demean CS")
    parser.add_argument(
        "--panel-csv",
        type=Path,
        default=REPO_ROOT
        / "output"
        / "did-cs-whitepaper-threshold"
        / "did_panel_data.csv",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DOCS_ROBUSTNESS,
    )
    args = parser.parse_args()

    panel = _load_panel(args.panel_csv)
    logger.info("Loaded panel: %s rows from %s", len(panel), args.panel_csv)

    raw_res = _run_branch(panel, label="raw", demean=False)
    dem_res = _run_branch(panel, label="month_demeaned", demean=True)

    comparison = pd.DataFrame(
        [
            {
                k: v
                for k, v in raw_res.items()
                if k != "cs_cohort_dynamics" and k != "cs_event_study"
            },
            {
                k: v
                for k, v in dem_res.items()
                if k != "cs_cohort_dynamics" and k != "cs_event_study"
            },
        ]
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = args.out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = args.out_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    comparison.to_csv(tables_dir / "seasonality_comparison.csv", index=False)
    _write_seasonality_latex(comparison, tables_dir / "seasonality_comparison.tex")
    raw_dyn = raw_res["cs_cohort_dynamics"]
    dem_dyn = dem_res["cs_cohort_dynamics"]
    if isinstance(raw_dyn, pd.DataFrame):
        raw_dyn.to_csv(tables_dir / "seasonality_raw_cohort_dynamics.csv", index=False)
    if isinstance(dem_dyn, pd.DataFrame):
        dem_dyn.to_csv(
            tables_dir / "seasonality_demean_cohort_dynamics.csv", index=False
        )
    _plot_cohort_comparison(
        raw_dyn,
        dem_dyn,
        fig_dir / "did_cohort_dynamics_seasonality_compare.png",
    )
    _write_memo(comparison, args.out_dir / "SEASONALITY_DIAGNOSTIC.md")

    logger.info("Wrote %s", tables_dir / "seasonality_comparison.csv")
    logger.info("Wrote %s", args.out_dir / "SEASONALITY_DIAGNOSTIC.md")


if __name__ == "__main__":
    main()
