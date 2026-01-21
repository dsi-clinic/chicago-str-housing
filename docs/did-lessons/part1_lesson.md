# Part 1: Causal Inference & Research Design

## Introduction

This quarter we're asking: **Do short-term rental restrictions actually affect housing costs?**

This seems like a simple question, but answering it correctly is surprisingly difficult. We can't just compare rents in areas with restrictions to areas without—there might be other differences between those areas that explain any rent differences we observe.

To answer this question properly, we need to understand **causal inference**: the science of determining whether one thing actually causes another.

---

## What is Causality?

**Causation** means one variable directly produces a change in another. If A causes B, then changing A will change B.

**Correlation** means two variables move together—when one goes up, the other tends to go up (or down). But correlation doesn't tell us *why* they move together.

**The fundamental problem of causal inference:** We can never directly observe causation. We can only observe what happened, not what *would have happened* if things were different.

This "what would have happened" is called the **counterfactual**. If a tract adopted STR restrictions, we can observe its rents afterward. But we can never observe what its rents would have been if it hadn't adopted restrictions. That's the counterfactual we need to estimate.

---

## Why Correlation ≠ Causation

Three problems make it hard to infer causation from correlation:

### 1. Confounding Variables

A **confounder** is a third variable that affects both the treatment and the outcome, creating a spurious relationship.

**Example:** Ice cream sales and drowning deaths are correlated. Does ice cream cause drowning?

No. Summer weather is the confounder:
- Hot weather → more ice cream sales
- Hot weather → more swimming → more drownings

The correlation between ice cream and drowning is real, but ice cream doesn't *cause* drowning.

**In our context:** Wealthier neighborhoods might both (a) adopt STR restrictions earlier AND (b) have different rent trends. Wealth would be a confounder.

### 2. Reverse Causality

Sometimes the direction of causation is the opposite of what we assume.

**Example:** Areas with more police have more crime. Do police cause crime?

No. The causation runs the other way:
- High crime → city deploys more police

**In our context:** Maybe neighborhoods with rapidly rising rents are more likely to adopt STR restrictions (residents want to slow rent growth). Then rising rents cause restrictions, not the other way around.

### 3. Selection Bias

**Selection bias** occurs when treated and control groups differ in ways that affect outcomes, beyond just the treatment.

**Example:** College graduates earn more than non-graduates. Does college cause higher earnings?

Maybe partly, but there's selection: people who go to college may be more motivated, have more resources, or have higher ability. These factors affect earnings regardless of college attendance.

**In our context:** Buildings that opt into STR restrictions might be systematically different from buildings that don't—different types of residents, different management, different neighborhood characteristics.

---

## Identification Strategies

To establish causation, we need an **identification strategy**—a research design that isolates the causal effect from confounding, reverse causality, and selection bias.

### Randomized Controlled Trials (RCTs)

The gold standard. Randomly assign treatment to some units and not others.

- Random assignment ensures treated and control groups are identical on average
- Any difference in outcomes must be due to the treatment
- **Example:** Medical drug trials, A/B testing in tech

**Problem:** We can't randomly assign STR restrictions to neighborhoods. Ethics and politics prevent it.

### Natural Experiments

Sometimes nature or policy creates variation that mimics randomization.

- Treatment assignment happens for reasons unrelated to outcomes
- Researchers exploit this "as-if random" variation
- **Examples:** Lottery winners (random wealth), policy changes affecting some but not others

### Difference-in-Differences (DiD)

A type of natural experiment that uses variation in treatment **timing**.

- Compare changes over time between treated and control groups
- Removes both pre-existing differences AND common time trends
- **Key assumption:** Without treatment, both groups would have followed parallel trends

This is what we'll use. The staggered rollout of STR restrictions in Chicago creates the variation we need.

---

## Difference-in-Differences: The Core Idea

### A Simple Example

Imagine we have two groups of tracts:
- **Treatment group:** Tracts that adopted STR restrictions in 2016
- **Control group:** Tracts that never adopted restrictions

We observe average rents before (2015) and after (2016) the policy:

| Group | Before (2015) | After (2016) | Change |
|-------|---------------|--------------|--------|
| Control | $1,200 | $1,250 | +$50 |
| Treatment | $1,400 | $1,420 | +$20 |

### The Wrong Approaches

**Wrong approach #1:** Compare treatment vs. control after treatment.

Treatment rents ($1,420) are higher than control rents ($1,250). Does the policy increase rents by $170?

No. Treatment tracts had higher rents *before* the policy too. The $170 difference includes pre-existing differences, not just the policy effect.

**Wrong approach #2:** Compare before vs. after for treatment group only.

Treatment rents went from $1,400 to $1,420, an increase of $20. Is the policy effect +$20?

No. Rents might have increased anyway due to inflation, economic growth, etc. We can't separate the policy effect from the time trend.

### The DiD Approach

DiD uses both comparisons together to isolate the causal effect.

**Step 1:** Calculate the change for each group.
- Control group change: $1,250 - $1,200 = +$50
- Treatment group change: $1,420 - $1,400 = +$20

**Step 2:** Take the difference of these differences.
- DiD = Treatment change - Control change
- DiD = +$20 - (+$50) = **-$30**

**Interpretation:** STR restrictions reduced rents by $30/month.

### Why This Works

The control group's change (+$50) represents what would have happened to the treatment group *without* treatment. This is our estimate of the counterfactual.

The treatment group only increased by $20. The difference (-$30) is the treatment effect.

DiD removes:
- **Pre-existing differences:** By looking at *changes* rather than levels
- **Common time trends:** By subtracting the control group's change

---

## The Parallel Trends Assumption

DiD relies on one critical assumption: **parallel trends**.

### What It Means

In the absence of treatment, the treated and control groups would have followed the same trend over time. The gap between them would have remained constant.

**Example with numbers:**

| Year | Control | Treatment | Gap |
|------|---------|-----------|-----|
| 2014 | $1,100 | $1,300 | $200 |
| 2015 | $1,200 | $1,400 | $200 |
| 2016 (treatment) | $1,300 | $1,470 | $170 |
| 2017 | $1,400 | $1,540 | $140 |

Before treatment (2014-2015): Both groups increase by $100/year. The gap stays constant at $200. **Trends are parallel.**

After treatment (2016+): Control keeps increasing by $100/year. Treatment only increases by $70/year. The gap shrinks. **Treatment caused the divergence.**

If parallel trends held without treatment, the treatment group would have been at $1,500 in 2016 and $1,600 in 2017. The treatment effect is the difference between actual and counterfactual: $1,470 - $1,500 = -$30.

### Why It Matters

If trends weren't parallel before treatment, our DiD estimate would be biased.

**Example of violation:** Suppose treatment tracts were already experiencing slower rent growth before the policy (maybe they're declining neighborhoods). Then:
- We'd attribute slower growth to the policy
- But it was happening anyway
- We'd overestimate the policy's rent-reducing effect

### Testing the Assumption

We can't directly test parallel trends—we never observe the counterfactual. But we can check **pre-treatment trends**:
- If trends were parallel before treatment, they probably would have continued
- If trends were diverging before treatment, the assumption is suspect

This is what **event study analysis** does: it plots the treatment effect for each time period, including periods before treatment. Pre-treatment effects should be near zero.

---

## Staggered Treatment

Our setting is more complex than the simple 2×2 example. Different tracts adopted STR restrictions at different times between 2015 and 2024.

### Why This Helps

Staggered treatment actually helps us:
- More variation to exploit
- Later-treated units serve as controls for earlier-treated units
- Can test parallel trends across multiple pre-periods

### How It Works

Consider three tracts:
- **Tract A:** Adopted restrictions in 2016
- **Tract B:** Adopted restrictions in 2018
- **Tract C:** Never adopted restrictions

| Year | Tract A | Tract B | Tract C |
|------|---------|---------|---------|
| 2015 | Control | Control | Control |
| 2016 | **Treated** | Control | Control |
| 2017 | Treated | Control | Control |
| 2018 | Treated | **Treated** | Control |
| 2019 | Treated | Treated | Control |

In 2016-2017, Tract B serves as a control for Tract A.
In 2018+, both A and B are treated, and only C is a control.

### The Panel Data Approach

With staggered treatment, we use **panel data** (observations of the same units over multiple time periods) and estimate:

```
rent = β₀ + β₁(treated) + (tract fixed effects) + (time fixed effects) + ε
```

- **Tract fixed effects:** Control for permanent differences between tracts
- **Time fixed effects:** Control for shocks common to all tracts in each period
- **β₁:** The treatment effect—how much rents change when a tract becomes treated

This is called **two-way fixed effects (TWFE)** estimation.

---

## Summary

1. **Correlation ≠ Causation** because of confounding, reverse causality, and selection bias.

2. **Identification strategies** like RCTs and natural experiments help isolate causal effects.

3. **Difference-in-Differences** compares changes over time between treated and control groups, removing both pre-existing differences and common time trends.

4. **Parallel trends** is the key assumption: without treatment, groups would have followed the same trajectory.

5. **Staggered treatment** means different units are treated at different times. Later-treated units serve as controls for earlier-treated ones.

6. **Two-way fixed effects** is the estimation approach for staggered DiD with panel data.

