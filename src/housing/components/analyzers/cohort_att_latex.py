"""Build LaTeX rows for cohort-level CS ATT summary tables."""

from __future__ import annotations

import pandas as pd

MIN_YM_LEN = 7
HIGHLIGHT_COHORT_SUFFIX = "2019-10"
CLEAN_PRETREND_MAX_SIG = 2


def _cohort_ym(cohort: object) -> str:
    raw = str(cohort)
    return raw[:MIN_YM_LEN] if len(raw) >= MIN_YM_LEN else raw


def build_cohort_att_table_lines(
    att_summary: pd.DataFrame,
    pretrend_sig: pd.DataFrame | None,
    *,
    highlight_cohort: str = HIGHLIGHT_COHORT_SUFFIX,
) -> list[str]:
    """Return booktabs table lines (without begin/end) for cohort ATTs."""
    cohort_rows = att_summary[att_summary["level"] == "cohort"].copy()
    if cohort_rows.empty:
        return []

    if pretrend_sig is not None and not pretrend_sig.empty:
        sig = pretrend_sig.copy()
        sig["cohort"] = sig["cohort"].astype(str)
        cohort_rows["cohort"] = cohort_rows["cohort"].astype(str)
        cohort_rows = cohort_rows.merge(sig, on="cohort", how="left")
    else:
        cohort_rows["n_significant_pre_coefs"] = pd.NA

    cohort_rows["_sort_key"] = cohort_rows["cohort"].map(_cohort_ym)
    cohort_rows = cohort_rows.sort_values("_sort_key")

    lines = [
        "% Auto-generated",
        "\\begin{tabular}{@{} l r r r r c @{}}",
        "\\toprule",
        ("Cohort & $n$ & ATT (\\$/mo.) & SE & " "Pre-violations & Clean \\\\"),
        "\\midrule",
    ]

    for _, row in cohort_rows.iterrows():
        ym = _cohort_ym(row["cohort"])
        n_tr = row.get("n_treated", pd.NA)
        n_s = str(int(n_tr)) if pd.notna(n_tr) else "---"
        att = float(row["att"]) if pd.notna(row.get("att")) else float("nan")
        se = float(row["se"]) if pd.notna(row.get("se")) else float("nan")
        att_s = f"{att:,.1f}".replace(",", "{,}") if att == att else "---"
        se_s = f"({se:,.2f})".replace(",", "{,}") if se == se else "---"
        n_sig = row.get("n_significant_pre_coefs", pd.NA)
        if pd.notna(n_sig):
            n_pre = row.get("n_pre_periods", 11)
            n_pre_i = int(n_pre) if pd.notna(n_pre) else 11
            viol_s = f"{int(n_sig)}/{n_pre_i}"
            clean = "Yes" if int(n_sig) <= CLEAN_PRETREND_MAX_SIG else "No"
        else:
            viol_s = "---"
            clean = "---"

        line = f"{ym} & {n_s} & {att_s} & {se_s} & {viol_s} & {clean} \\\\"
        if highlight_cohort in ym:
            line = line.replace(f"{ym} &", f"\\textbf{{{ym}}} &")
        lines.append(line)

    lines.extend(["\\bottomrule", "\\end{tabular}"])
    return lines
