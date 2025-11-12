## Cluster Analysis Overview

This document summarizes the clustering workflow implemented in `src/housing/scripts/clustering_analysis.py` and provides guidance for interpreting the generated outputs in `output/clustering/`.

### Workflow Highlights
- **Inputs**: Standardized tract-level variables (see `clustering_data_scaled.csv`).
- **Pre-processing**: Step 3 filters the data to tracts used in clustering, calculates Moran’s I, and optionally renders a scatterplot matrix (run the script with `--scatter-matrix` to include this diagnostic).
- **Clustering Methods**:  
  - K-means with `k=6` (default) on the standardized variables.  
  - Ward hierarchical clustering (unconstrained) and two regionalized variants using Queen contiguity and 4-nearest-neighbor constraints.  
  - All Ward runs also default to 6 clusters for comparability.
- **Outputs**: Each clustering solution produces maps, cluster profiles, size plots, attribute distributions, and statistical summaries. Shared color palettes ensure visual consistency across outputs.
- **Evaluation Metrics**:  
  - Calinski–Harabasz scores (`cluster_coherence_scores.csv`) compare feature coherence across clustering strategies.  
  - Adjusted Mutual Information matrix (`cluster_similarity_matrix.csv`) quantifies how similar each clustering solution is to the others.  
  - Moran’s I results (`morans_i_results.csv`) measure spatial autocorrelation of every variable prior to clustering.

### Key Artifacts and Interpretation

| Output | Description | How to Read |
| --- | --- | --- |
| `kmeans_cluster_map.png`, `ward*_cluster_map.png` | Choropleths mapping tract-to-cluster assignments. | Identify spatial patterns, emerging neighborhoods, or contiguous regions. Compare K-means vs. Ward variants for spatial coherence. |
| `kmeans_cluster_profiles.png`, `ward*_cluster_profiles.png` | Transposed tables summarizing cluster counts and mean attribute values. | Row labels (attributes) clarify profiles. Use scientific notation cues for small values and thousands separators for large values. Since K-means and Ward share color palettes, matching colors across maps and tables aid interpretation. |
| `kmeans_cluster_sizes.png`, `ward*_cluster_sizes.png` | Bar charts displaying cluster membership counts. | Quickly assess cluster balance/imbalance. Bars are annotated with integer counts, and color matches mapping/table outputs. |
| `kmeans_attribute_distributions.png`, `ward*_attribute_distributions.png` | Faceted KDE plots of each variable stratified by cluster. | Inspect distribution overlap (separation) across clusters for each attribute. The shared palette clarifies which cluster is which. |
| `kmeans_cluster_kruskal.png` | Kruskal–Wallis stats for each attribute. | Significant (low p-value) attributes differ across clusters. The table omits adjusted p-values to keep values readable. |
| `kmeans_cluster_pairwise_ks.png` | Pairwise Kolmogorov–Smirnov tests (per attribute). | Highlights specific cluster pairs with distributional differences. Use alongside the KDE facets to contextualize magnitude/direction. |
| `kmeans_cluster_permanova.png`, `kmeans_cluster_manova.png` | Multivariate tests (PERMANOVA, MANOVA). | PERMANOVA pseudo-F and p-value summarize overall multivariate separation. MANOVA offers Wilks’ lambda, F, and p-value for centroid differences. |
| `kmeans_elbow_plot.png` + `kmeans_elbow_scores.csv` | K-means inertia across tested k values. | Use the bend (“elbow”) to justify the default k=6; the CSV lists exact inertia values. |
| `kmeans_ward_comparison_map.png` | Side-by-side K-means vs. Ward choropleths. | Compare spatial footprints directly; colors stay consistent for K-means, while Ward uses a contrasting palette. |
| `cluster_coherence_scores.csv` | Calinski–Harabasz scores for each solution. | Higher scores imply tighter clusters relative to separation; compare rows to pick the most coherent approach. |
| `cluster_similarity_matrix.csv` | Adjusted Mutual Information matrix. | Values (0–1) quantify similarity; diagonal is 1. Use to judge whether different algorithms produce comparable partitions. |


