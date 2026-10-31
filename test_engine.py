"""Tests for the deterministic GraphPulse engine."""

from pathlib import Path

from engine import DEFAULT_GRAPH_PATH, GraphMetrics, load_graph_metrics


def test_demo_graph_loads_with_nodes() -> None:
    """The generated demo graph must provide a non-empty strict metrics object."""
    assert Path(DEFAULT_GRAPH_PATH).is_file()
    metrics = load_graph_metrics(DEFAULT_GRAPH_PATH)
    assert isinstance(metrics, GraphMetrics)
    assert metrics.total_nodes > 0
    assert metrics.total_edges >= 0


def test_graph_metrics_have_consistent_edge_counts() -> None:
    """Confidence buckets cannot exceed the total edge count."""
    metrics = load_graph_metrics(DEFAULT_GRAPH_PATH)
    assert metrics.extracted_edges + metrics.inferred_edges <= metrics.total_edges
