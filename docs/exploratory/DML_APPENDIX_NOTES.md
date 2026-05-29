# Double ML (orthogonal scores) versus CS double robustness — appendix wording

Chernozhukov et al. (Econometrica, 2018; bibliographic entry in `literature/references.bib`) develop **orthogonalized score functions with cross-fit nuisance estimation** (“Double ML”). That is distinct from Sant'Anna–Zhao **doubly robust DiD**, which averages outcome-regression and IPW contrasts on a staggered timetable.

Before running **econml** or [**DoubleML**](https://docs.doubleml.org/) on this tract panel:

### Panel structure

Treatments stagger by tract and calendar month; nuisance models must acknowledge **persistent tract heterogeneity**, **seasonality**, or **explicit relative-time** structure if you coerce the problem into pseudo-cross-section waves.

### What to benchmark

Prefer reporting **overlap with CS overall ATT**, **sign alignment on dynamic effects**, not exact numeric equality.

### Complexity budget

Specify one transparent target (overall late vs early contrast or event window) before expanding to high-dimensional covariate dictionaries.

Use this appendix as a methodological placeholder; full Double ML estimation is exploratory and secondary to finalized Callaway–Sant’Anna event studies with documented controls.
