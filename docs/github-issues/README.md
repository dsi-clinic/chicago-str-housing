# GitHub issue stubs (paper + robustness feedback)

Bodies used for `gh issue create` are kept under [`bodies/`](bodies/) for version control and reuse.

## Canonical repo (`dsi-clinic/chicago-str-housing`)

Issues are tracked on **https://github.com/dsi-clinic/chicago-str-housing** (not the personal fork).

| # | Title |
|---|--------|
| [Issue 80](https://github.com/dsi-clinic/chicago-str-housing/issues/80) | Paper: lead with naive/simple results, then preferred specification |
| [Issue 81](https://github.com/dsi-clinic/chicago-str-housing/issues/81) | Robustness sweep: trend-matching k_neighbors = 1…5 (default 3) |
| [Issue 82](https://github.com/dsi-clinic/chicago-str-housing/issues/82) | Robustness sweep: threshold intensity (percentile / treatment sensitivity) |
| [Issue 83](https://github.com/dsi-clinic/chicago-str-housing/issues/83) | Lock preferred specification; dashboard as paper companion |

Duplicate copies were also opened earlier on fork `anfelipecb/chicago-housing-2025` (#1–#4); prefer closing those in favor of **80–83** above.

## Git remotes in this checkout

Your local `git remote -v` may show `origin` → personal fork and `upstream` → another DSI repo name. For **issues and canonical collaboration**, use **`dsi-clinic/chicago-str-housing`**. Optional local alias:

```bash
git remote add canonical git@github.com:dsi-clinic/chicago-str-housing.git
# or HTTPS: https://github.com/dsi-clinic/chicago-str-housing.git
```

Then: `gh issue list --repo dsi-clinic/chicago-str-housing` or `git fetch canonical`.
