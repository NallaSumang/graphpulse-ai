"""Streamlit dashboard for GraphPulse graph auditing."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from engine import (
    DEFAULT_GRAPH_PATH,
    GraphMetrics,
    affected_nodes,
    explain_node,
    load_graph_metrics,
    trace_path,
    update_graph,
)
from gemma_auditor import GemmaAuditor


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_TARGET = PROJECT_ROOT / "demo_codebase"
REPORT_PATH = DEFAULT_TARGET / "graphify-out" / "GRAPH_REPORT.md"
HTML_PATH = DEFAULT_TARGET / "graphify-out" / "graph.html"


def main() -> None:
    st.set_page_config(page_title="GraphPulse", page_icon="🕸️", layout="wide")
    st.title("GraphPulse")
    st.caption("Deterministic Graphify topology plus Gemma 4 architectural blast-radius analysis")

    runtime_label, api_key, rebuild_requested = _render_sidebar()
    if rebuild_requested:
        try:
            with st.spinner("Rebuilding the knowledge graph..."):
                update_graph(DEFAULT_TARGET)
            st.success("Knowledge graph rebuilt.")
        except (FileNotFoundError, RuntimeError) as exc:
            st.error(str(exc))

    try:
        metrics = load_graph_metrics(DEFAULT_GRAPH_PATH)
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.error(f"Unable to load the demo graph: {exc}")
        st.info("Run Graphify against demo_codebase before launching the dashboard.")
        return

    _render_kpis(metrics)
    topology_tab, query_tab, auditor_tab = st.tabs(
        [
            "Interactive Topology",
            "Deterministic AST Queries",
            "Gemma 4 Multimodal Blast-Radius Auditor",
        ]
    )
    with topology_tab:
        _render_topology()
    with query_tab:
        _render_queries(metrics.node_labels)
    with auditor_tab:
        _render_auditor(runtime_label, api_key)


def _render_sidebar() -> tuple[str, str, bool]:
    st.sidebar.header("Runtime")
    runtime_label = st.sidebar.radio(
        "Gemma runtime",
        ["Gemini API (gemma-4-26b-a4b-it)", "Local Ollama (gemma4:e4b)"],
    )
    api_key = st.sidebar.text_input(
        "GEMINI_API_KEY",
        value="",
        type="password",
        help="Used only for the Gemini API runtime.",
    )
    rebuild = st.sidebar.button("Rebuild Knowledge Graph", type="primary")
    st.sidebar.caption(f"Target: `{DEFAULT_TARGET.relative_to(PROJECT_ROOT)}`")
    return runtime_label, api_key, rebuild


def _render_kpis(metrics: GraphMetrics) -> None:
    columns = st.columns(4)
    values = [
        ("AST Nodes", metrics.total_nodes),
        ("EXTRACTED Edges", metrics.extracted_edges),
        ("INFERRED Edges", metrics.inferred_edges),
        ("Estimated Token Savings", f"{metrics.estimated_token_savings_percent:.1f}%"),
    ]
    for column, (label, value) in zip(columns, values):
        column.metric(label, value)


def _render_topology() -> None:
    st.subheader("Knowledge graph topology")
    if HTML_PATH.is_file():
        components.html(HTML_PATH.read_text(encoding="utf-8"), height=720, scrolling=True)
    elif DEFAULT_GRAPH_PATH.is_file():
        components.html(_fallback_network_html(), height=720, scrolling=True)
    else:
        st.warning("graph.html and graph.json are not available.")

    st.subheader("Graphify audit report")
    if REPORT_PATH.is_file():
        st.markdown(REPORT_PATH.read_text(encoding="utf-8"))
    else:
        st.info("GRAPH_REPORT.md is not available yet.")


def _render_queries(labels: list[str]) -> None:
    if not labels:
        st.info("No node labels are available.")
        return
    st.subheader("Path trace")
    source = st.selectbox("Source node", labels, key="path_source")
    target = st.selectbox("Target node", labels, index=min(1, len(labels) - 1), key="path_target")
    if st.button("Trace shortest path"):
        try:
            result = trace_path(source, target, DEFAULT_GRAPH_PATH)
            st.json(result.model_dump())
        except RuntimeError as exc:
            st.error(str(exc))

    st.subheader("Node neighborhood")
    explain_target = st.selectbox("Node to explain", labels, key="explain_target")
    if st.button("Explain node"):
        try:
            st.code(explain_node(explain_target, DEFAULT_GRAPH_PATH))
        except RuntimeError as exc:
            st.error(str(exc))

    st.subheader("Reverse dependents")
    affected_target = st.selectbox("Node whose dependents to inspect", labels, key="affected_target")
    if st.button("Find affected nodes"):
        try:
            st.code(affected_nodes(affected_target, DEFAULT_GRAPH_PATH))
        except RuntimeError as exc:
            st.error(str(exc))


def _render_auditor(runtime_label: str, api_key: str) -> None:
    st.subheader("Gemma 4 architectural audit")
    question = st.text_area(
        "Refactoring or PR impact question",
        placeholder="What is the blast radius of moving risk evaluation behind an async queue?",
        height=140,
    )
    screenshot = st.file_uploader(
        "Optional graph cluster screenshot",
        type=["png", "jpg", "jpeg"],
    )
    if st.button("Run Gemma 4 Audit", type="primary"):
        runtime = "gemini" if runtime_label.startswith("Gemini") else "ollama"
        try:
            auditor = GemmaAuditor(runtime=runtime, api_key=api_key or None)
            with st.spinner("Auditing graph evidence..."):
                answer = auditor.audit(
                    question=question,
                    graph_json_path=DEFAULT_GRAPH_PATH,
                    report_path=REPORT_PATH,
                    screenshot=screenshot.getvalue() if screenshot else None,
                    screenshot_name=screenshot.name if screenshot else None,
                )
            st.markdown(answer)
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            st.error(str(exc))


def _fallback_network_html() -> str:
    graph = json.loads(DEFAULT_GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", graph.get("links", []))
    node_data = [
        {"id": node.get("id"), "label": node.get("label", node.get("name", node.get("id", "")))}
        for node in nodes
        if isinstance(node, dict)
    ]
    edge_data = [
        {"from": edge.get("source"), "to": edge.get("target")}
        for edge in edges
        if isinstance(edge, dict) and edge.get("source") is not None and edge.get("target") is not None
    ]
    return f"""<!doctype html>
<html><head><script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>#network {{ width:100%; height:680px; border:1px solid #ddd; }}</style></head>
<body><div id="network"></div><script>
const nodes = new vis.DataSet({json.dumps(node_data)});
const edges = new vis.DataSet({json.dumps(edge_data)});
new vis.Network(document.getElementById("network"), {{nodes, edges}}, {{
  physics: {{stabilization: true}},
  nodes: {{shape: "dot", font: {{size: 12}}}}
}});
</script></body></html>"""


if __name__ == "__main__":
    main()
