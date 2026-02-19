"""Deep diagnostic for DiD panel data and estimator analysis."""
import sys
import os
import logging

sys.path.insert(0, str(os.path.join(os.path.dirname(__file__), "..", "..")))
logging.basicConfig(level=logging.WARNING)

import pandas as pd
import numpy as np

from pipeline import Pipeline
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.processors.time_series_zip_to_tract import TimeSeriesZipToTractProcessor
from housing.components.processors.treatment_indicator import TreatmentIndicatorProcessor


def main():
    pipeline = Pipeline("diag")
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(TimeSeriesRentalLoader())
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())
    pipeline.register_component(TreatmentIndicatorProcessor())
    pipeline.execute()

    df = pipeline.context["did_panel"]

    # 1. Treatment cohort detail
    print("=== TREATMENT COHORT DETAIL ===")
    first_treat = df[df["treated"] == 1].groupby("tract_geoid")["month"].min()
    cohort_sizes = first_treat.value_counts().sort_index()
    print(f"Total treatment cohorts: {len(cohort_sizes)}")
    print(f"Cohorts with >= 5 tracts: {(cohort_sizes >= 5).sum()}")
    print(f"Cohorts with >= 10 tracts: {(cohort_sizes >= 10).sum()}")
    print()
    print("Cohort date    | Tracts")
    print("-" * 30)
    for date, count in cohort_sizes.items():
        print(f"  {str(date)[:10]} | {count}")

    # 2. Monthly date range
    print()
    print("=== DATE RANGE ===")
    months = sorted(df["month"].unique())
    print(f"First month: {months[0]}")
    print(f"Last month:  {months[-1]}")
    print(f"Total months: {len(months)}")
    date_range = pd.date_range(months[0], months[-1], freq="ME")
    missing_months = set(date_range) - set(months)
    print(f"Missing months in range: {len(missing_months)}")

    # 3. Pre-treatment parallel trends
    print()
    print("=== PRE-TREATMENT PARALLEL TRENDS CHECK ===")
    never_treated_mask = df.groupby("tract_geoid")["treated"].transform("max") == 0
    treated_mask = ~never_treated_mask

    early_months = months[:24]
    for label, mask in [("Never-treated", never_treated_mask), ("Treated (pre-treat)", treated_mask)]:
        sub = df[mask & df["month"].isin(early_months)]
        if label == "Treated (pre-treat)":
            sub = sub[sub["treated"] == 0]
        monthly_avg = sub.groupby("month")["rental_price"].mean()
        if len(monthly_avg) >= 2:
            growth = ((monthly_avg.iloc[-1] / monthly_avg.iloc[0]) - 1) * 100
            print(f"{label}: first=${monthly_avg.iloc[0]:.0f}, last=${monthly_avg.iloc[-1]:.0f}, growth={growth:.1f}%")

    # 4. STR prohibition date analysis
    print()
    print("=== STR PROHIBITION DATE QUALITY ===")
    str_data = pipeline.context.get("str_prohibition_data")
    if str_data is not None:
        date_col = "prohibition_date" if "prohibition_date" in str_data.columns else "signed_date"
        dates = pd.to_datetime(str_data[date_col])
        print(f"Total buildings: {len(str_data)}")
        print(f"Date range: {dates.min()} to {dates.max()}")
        pre_2015 = (dates < "2015-01-01").sum()
        print(f"Buildings with date before 2015: {pre_2015}")
        by_year = dates.dt.year.value_counts().sort_index()
        print("Prohibitions by year:")
        for year, count in by_year.items():
            print(f"  {year}: {count}")

    # 5. Relative time distribution
    print()
    print("=== RELATIVE TIME DISTRIBUTION (treated tracts only) ===")
    rel = df.loc[df["months_since_treatment"].notna(), "months_since_treatment"]
    print(f"Total obs with rel_time: {len(rel)}")
    bins = [-999, -36, -24, -12, -6, -1, 0, 6, 12, 24, 36, 999]
    labels = ["<-36", "-36:-24", "-24:-12", "-12:-6", "-6:-1", "-1:0", "0:5", "6:11", "12:23", "24:35", "36+"]
    rel_binned = pd.cut(rel, bins=bins, labels=labels, right=False)
    dist = rel_binned.value_counts().sort_index()
    for label, count in dist.items():
        print(f"  {str(label):>10}: {count:>6}")

    # 6. Rental price evolution (annual)
    print()
    print("=== RENTAL PRICE EVOLUTION (annual averages) ===")
    df_copy = df.copy()
    df_copy["year"] = df_copy["month"].dt.year
    df_copy["group"] = np.where(never_treated_mask, "Never-treated", "Treated")
    annual = df_copy.groupby(["year", "group"])["rental_price"].mean().unstack()
    print(annual.round(0).to_string())

    # 7. Top 10 cohorts
    print()
    print("=== TOP 10 COHORTS (most tracts) ===")
    top_cohorts = cohort_sizes.nlargest(10)
    for date, count in top_cohorts.items():
        pre_months = len([m for m in months if m < date])
        post_months = len([m for m in months if m >= date])
        print(f"  {str(date)[:10]}: {count:3d} tracts, {pre_months:3d} pre, {post_months:3d} post")

    # 8. Never-treated rental price stats
    print()
    print("=== NEVER-TREATED TRACTS ===")
    nt_df = df[never_treated_mask]
    print(f"Never-treated tracts: {nt_df['tract_geoid'].nunique()}")
    print(f"Mean rent: ${nt_df['rental_price'].mean():.0f}")
    print(f"Std rent: ${nt_df['rental_price'].std():.0f}")

    # 9. Check for outlier tracts
    print()
    print("=== RENTAL PRICE OUTLIER CHECK ===")
    tract_means = df.groupby("tract_geoid")["rental_price"].mean()
    q1, q3 = tract_means.quantile(0.25), tract_means.quantile(0.75)
    iqr = q3 - q1
    low_outliers = tract_means[tract_means < q1 - 1.5 * iqr]
    high_outliers = tract_means[tract_means > q3 + 1.5 * iqr]
    print(f"Tract mean rent: Q1=${q1:.0f}, Q3=${q3:.0f}, IQR=${iqr:.0f}")
    print(f"Low outlier tracts (< ${q1 - 1.5*iqr:.0f}): {len(low_outliers)}")
    print(f"High outlier tracts (> ${q3 + 1.5*iqr:.0f}): {len(high_outliers)}")

    # 10. CS-relevant: cohort sizes meeting min threshold
    print()
    print("=== CALLAWAY-SANTANNA ESTIMATION FEASIBILITY ===")
    for threshold in [5, 10, 20]:
        n_valid = (cohort_sizes >= threshold).sum()
        n_tracts = cohort_sizes[cohort_sizes >= threshold].sum()
        print(f"  min_cohort_size={threshold}: {n_valid} cohorts, {n_tracts} tracts")

    never_count = df[never_treated_mask]["tract_geoid"].nunique()
    print(f"  Never-treated comparison pool: {never_count} tracts")


if __name__ == "__main__":
    main()
