"""Cluster analysis package."""

from .analysis import (
    KMeansClusteringResult,
    attach_cluster_labels,
    build_tidy_cluster_frame,
    compute_coherence_scores,
    compute_similarity_matrix,
    kruskal_wallis_by_attribute,
    pairwise_ks_tests,
    prepare_cluster_analysis_data,
    run_kmeans_workflow,
    run_manova_test,
    run_permanova_test,
    run_ward_clustering,
    summarise_clusters,
)
from .figures import (
    create_attribute_distribution_facets,
    create_cluster_comparison_map,
    create_cluster_map,
    create_cluster_sizes_plot,
    create_kmeans_elbow_plot,
    dataframe_to_table_png,
    render_cluster_summary_table,
)

__all__ = [
    "KMeansClusteringResult",
    "attach_cluster_labels",
    "build_tidy_cluster_frame",
    "compute_coherence_scores",
    "compute_similarity_matrix",
    "kruskal_wallis_by_attribute",
    "pairwise_ks_tests",
    "prepare_cluster_analysis_data",
    "run_kmeans_workflow",
    "run_manova_test",
    "run_permanova_test",
    "run_ward_clustering",
    "summarise_clusters",
    "create_attribute_distribution_facets",
    "create_cluster_map",
    "create_cluster_comparison_map",
    "create_cluster_sizes_plot",
    "create_kmeans_elbow_plot",
    "dataframe_to_table_png",
    "render_cluster_summary_table",
]
