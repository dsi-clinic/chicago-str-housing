"""DiD Data Diagnostic Script.

Loads the DiD panel and analyzes data quality, treatment distribution,
rental prices, and potential issues for the event study.
"""
import logging
import os
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline import Pipeline
from housing.components.loaders.tract_boundaries import TractBoundariesLoader
from housing.components.loaders.zip_boundaries import ZipBoundariesLoader
from housing.components.loaders.str_prohibition_data import STRProhibitionDataLoader
from housing.components.loaders.time_series_rental_data import TimeSeriesRentalLoader
from housing.components.loaders.rental_data import RentalDataLoader
from housing.components.processors.zip_to_tract import ZipToTractProcessor
from housing.components.processors.time_series_zip_to_tract import TimeSeriesZipToTractProcessor
from housing.components.processors.treatment_indicator import TreatmentIndicatorProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_ROOT = Path(os.environ.get("DATA_DIR", "/project/data"))


def main():
    """Build DiD panel and run diagnostics."""
    print("=" * 70)
    print("DiD DATA DIAGNOSTIC")
    print("=" * 70)

    pipeline = Pipeline("DiD Diagnostic")
    pipeline.register_component(TractBoundariesLoader())
    pipeline.register_component(ZipBoundariesLoader())
    pipeline.register_component(STRProhibitionDataLoader(deduplicate_coords=True))
    pipeline.register_component(RentalDataLoader())
    pipeline.register_component(TimeSeriesRentalLoader())
    pipeline.register_component(ZipToTractProcessor())
    pipeline.register_component(TimeSeriesZipToTractProcessor())
    pipeline.register_component(TreatmentIndicatorProcessor())

    results = pipeline.execute()
    if not any(r.success for r in results):
        print("Pipeline failed. Check logs.")
        return

    df = pipeline.context.get("did_panel")
    if df is None:
        print("ERROR: did_panel not in context")
        return

    # 1. Panel structure
    print("\n1. PANEL STRUCTURE")
    print("-" * 40)
    n_tracts = df["tract_geoid"].nunique()
    n_months = df["month"].nunique()
    print(f"  Tracts: {n_tracts}")
    print(f"  Months: {n_months}")
    print(f"  Total obs: {len(df)}")
    print(f"  Expected if balanced: {n_tracts * n_months}")
    obs_per_tract = df.groupby("tract_geoid").size()
    print(f"  Obs per tract: min={obs_per_tract.min()}, max={obs_per_tract.max()}, mean={obs_per_tract.mean():.1f}")

    # 2. Treatment
    print("\n2. TREATMENT")
    print("-" * 40)
    ever_treated = df.groupby("tract_geoid")["treated"].max()
    n_treated = ever_treated.sum()
    n_never = len(ever_treated) - n_treated
    print(f"  Ever-treated tracts: {n_treated}")
    print(f"  Never-treated tracts: {n_never}")
    print(f"  Treated tract-months: {df['treated'].sum():,} / {len(df):,} ({100*df['treated'].mean():.1f}%)")

    # 3. months_since_treatment
    print("\n3. RELATIVE EVENT TIME (months_since_treatment)")
    print("-" * 40)
    rel = df["months_since_treatment"].dropna()
    if len(rel) > 0:
        print(f"  Treated obs with rel_time: {len(rel):,}")
        print(f"  Min: {int(rel.min())}, Max: {int(rel.max())}")
        ref_count = (df["months_since_treatment"].isna()).sum()
        print(f"  Never-treated (NaN -> coded as -1): {ref_count:,}")
        # Distribution of cohorts (first treatment month)
        first_treat = df[df["treated"] == 1].groupby("tract_geoid")["month"].min()
        print(f"  Treatment start dates: {first_treat.min()} to {first_treat.max()}")
        print(f"  Number of distinct treatment cohorts: {first_treat.nunique()}")

    # 4. Rental prices
    print("\n4. RENTAL PRICES ($)")
    print("-" * 40)
    valid = df["rental_price"].dropna()
    print(f"  Non-missing: {len(valid):,} / {len(df):,}")
    print(f"  Mean: ${valid.mean():.0f}")
    print(f"  Median: ${valid.median():.0f}")
    print(f"  Min: ${valid.min():.0f}, Max: ${valid.max():.0f}")
    print(f"  Std: ${valid.std():.0f}")

    # 5. Treated vs Never-treated levels
    print("\n5. RENTAL PRICE: TREATED vs NEVER-TREATED (pre-treatment only)")
    print("-" * 40)
    pre = df[df["treated"] == 0]  # pre-treatment for treated + all for never-treated
    treated_pre = pre[pre["months_since_treatment"].notna()]  # treated tracts, pre period
    never_pre = pre[pre["months_since_treatment"].isna()]     # never-treated
    if len(treated_pre) > 0 and len(never_pre) > 0:
        t_mean = treated_pre["rental_price"].mean()
        n_mean = never_pre["rental_price"].mean()
        print(f"  Treated (pre-treatment avg): ${t_mean:.0f}")
        print(f"  Never-treated (all periods avg): ${n_mean:.0f}")
        print(f"  Gap: ${t_mean - n_mean:.0f} ({(t_mean/n_mean - 1)*100:.1f}%)")

    # 6. Crosswalk coverage
    print("\n6. ZIP-TO-TRACT COVERAGE")
    print("-" * 40)
    crosswalk = pipeline.context.get("zip_to_tract_crosswalk")
    tract_bounds = pipeline.context.get("tract_boundaries")
    if crosswalk is not None and tract_bounds is not None:
        tracts_in_panel = set(df["tract_geoid"].unique())
        tracts_in_bounds = set(tract_bounds["tract_geoid"].unique())
        tracts_in_crosswalk = set(crosswalk["tract_geoid"].unique())
        print(f"  Tracts in boundaries: {len(tracts_in_bounds)}")
        print(f"  Tracts in crosswalk: {len(tracts_in_crosswalk)}")
        print(f"  Tracts in panel: {len(tracts_in_panel)}")
        not_in_crosswalk = tracts_in_bounds - tracts_in_crosswalk
        print(f"  Tracts in boundaries but not crosswalk: {len(not_in_crosswalk)} (no ZORI coverage)")

    # 7. Potential issues
    print("\n7. POTENTIAL DATA ISSUES")
    print("-" * 40)
    issues = []
    if n_never < 10:
        issues.append("Very few never-treated tracts - control group may be weak")
    if len(rel) == 0:
        issues.append("No treated observations with months_since_treatment")
    if valid.min() < 100 or valid.max() > 50000:
        issues.append(f"Rental prices outside typical range (${valid.min():.0f} - ${valid.max():.0f})")
    if obs_per_tract.nunique() > 1:
        issues.append("Unbalanced panel - some tracts missing months")
    if len(issues) == 0:
        print("  None detected.")
    else:
        for i in issues:
            print(f"  - {i}")

    # 8. Interpretation
    print("\n8. INTERPRETATION NOTES")
    print("-" * 40)
    print("  - TWFE event study can be biased with staggered treatment (Goodman-Bacon 2021)")
    print("  - Your did_twfe_cs_comparison_table.csv shows TWFE ~$240 vs CS ~$0-48 post-treatment")
    print("  - Callaway-Sant'Anna (CS) is more appropriate for staggered DiD")
    print("  - Large TWFE-CS gap suggests heterogeneous treatment effects / negative weighting")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
