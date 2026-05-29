---
layout: home
---

## The question

Chicago's [Shared Housing Ordinance](https://www.chicago.gov/content/dam/city/depts/bacp/Small%20Business%20Center/sharedhousingordinanceamendments.pdf) lets residential buildings opt into a prohibited-buildings list that bars short-term rentals. Hundreds of buildings have joined since 2015. Does removing Airbnb-style listings make neighborhoods more affordable for long-term renters — or does it actually push rents *up*?

## What we found

> **"STR prohibitions do not lower rents."**
> Banning short-term rentals in Chicago is associated with a *$3–10/month increase* in long-term rental prices — and the effect grows over time.


| Finding | Detail |
|---------|--------|
| **Average effect** | +$6/month in long-term rents (95 % CI: $3–10) |
| **Growing over time** | +$2.50 in year 1 → +$8.60 by year 3 |
| **Stronger where STR density is high** | Tracts with more Airbnb listings see larger increases |
| **Spillovers to neighbors** | Adjacent never-treated tracts see ~$18/month increases |

The mechanism is counterintuitive: prohibitions signal residential stability, attracting long-term renters and bidding up prices. The demand effect outweighs the supply gain.

## Read the research

<div style="display:flex; gap:1.5rem; flex-wrap:wrap; margin-top:0.5rem; margin-bottom:2rem;">
<a href="{{ "/str-paper/STR_POLICY_BRIEF/" | relative_url }}" style="flex:1; min-width:200px; padding:1rem 1.25rem; border:1px solid #ddd; border-radius:6px; text-decoration:none; color:inherit;">
<strong>Policy brief</strong><br>
<span style="font-size:0.9em; color:#555;">One-page summary for city leadership and stakeholders.</span>
</a>
<a href="{{ "/str-paper/STR_PROHIBITION_PAPER/" | relative_url }}" style="flex:1; min-width:200px; padding:1rem 1.25rem; border:1px solid #ddd; border-radius:6px; text-decoration:none; color:inherit;">
<strong>Technical paper</strong><br>
<span style="font-size:0.9em; color:#555;">Full methods, difference-in-differences results, robustness checks, and appendix.</span>
</a>
</div>

## About

This project was produced by the **University of Chicago Data Science Institute** in partnership with the **City of Chicago Department of Technology and Innovation**. The full analysis pipeline, data, and source code are available in the [GitHub repository](https://github.com/dsi-clinic/chicago-str-housing).
