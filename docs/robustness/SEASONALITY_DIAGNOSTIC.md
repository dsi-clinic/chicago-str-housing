# Calendar-month fixed effects diagnostic

Comparison of matched-sample Callaway--Sant'Anna on **raw** ZORI levels vs **panel-wide month-of-year demeaned** rents (same matching, $k=3$, five-feature).

## Results

| branch | matched_att | matched_se | pretrend_p | cohort_2019_10_sig_pre |
| --- | ---: | ---: | ---: | ---: |
| raw | 5.456416006902979 | 0.3895606130856879 | 0.0 | 2 |
| month_demeaned | 5.461873682166074 | 0.3906426057265623 | 0.0 | 2 |

- Pooled matched ATT change (abs): **$0.01/mo**
- 2019-10 cohort pre-violations (sig of 11): raw=2, demeaned=2
- Joint pre-trend $p$: raw=0, demeaned=0

## Recommendation

**Do not adopt for headline spec:** Either pooled ATT moves materially (>$3/mo) or 2019-10 pre-trends do not improve clearly. Report as appendix diagnostic only.

Figures: `docs/robustness/figures/did_cohort_dynamics_seasonality_compare.png`
