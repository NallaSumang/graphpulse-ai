"""Deterministic Graphify integration for the GraphPulse application."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_GRAPH_PATH = PROJECT_ROOT / "demo_codebase" / "graphify-out" / "graph.json"


class GraphMetrics(BaseModel):
    """Strict summary of a Graphify graph and its estimated token savings."""

    model_config = ConfigDict(extra="forbid", strict=True)

    node_labels: list[str] = Field(default_factory=list)
    total_nodes: int = Field(ge=0)
    total_edges: int = Field(ge=0)
    extracted_edges: int = Field(ge=0)
    inferred_edges: int = Field(ge=0)
    raw_grep_tokens: int = Field(ge=0)
    graph_tokens: int = Field(ge=0)
    estimated_token_savings: int = Field(ge=0)
    estimated_token_savings_percent: float = Field(ge=0, le=100)


class PathTraceResult(BaseModel):
    """Strict result returned by a deterministic Graphify path operation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    source: str
    target: str
    found: bool
    path: list[str] = Field(default_factory=list)
    raw_output: str


def _graphify_command() -> str:
    """Return the project-local Graphify executable, or the PATH fallback."""
    local_executable = PROJECT_ROOT / "venv" / "Scripts" / "graphify.exe"
    return str(local_executable) if local_executable.is_file() else "graphify"


def _run_graphify(arguments: Sequence[str]) -> str:
    """Run Graphify without a shell and surface failures with command context."""
    command = [_graphify_command(), *arguments]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        raise RuntimeError(
            f"Graphify command failed ({completed.returncode}): "
            f"{' '.join(command)}\n{detail}"
        )
    return completed.stdout.strip()


def update_graph(target_dir: str | os.PathLike[str]) -> str:
    """Incrementally update the Graphify graph for ``target_dir``."""
    target = Path(target_dir).resolve()
    if not target.is_dir():
        raise FileNotFoundError(f"Graphify target directory does not exist: {target}")
    return _run_graphify(["update", str(target)])


def query_graph(question: str, graph_json_path: str | os.PathLike[str]) -> str:
    """Run a Graphify natural-language query against a graph JSON file."""
    return _run_graphify(
        ["query", question, "--graph", str(Path(graph_json_path).resolve())]
    )


def trace_path(
    node_a: str,
    node_b: str,
    graph_json_path: str | os.PathLike[str],
) -> PathTraceResult:
    """Trace the shortest Graphify path between two node labels."""
    raw_output = _run_graphify(
        [
            "path",
            node_a,
            node_b,
            "--graph",
            str(Path(graph_json_path).resolve()),
        ]
    )
    path = _parse_path(raw_output)
    return PathTraceResult(
        source=node_a,
        target=node_b,
        found=bool(path) and not _looks_like_no_path(raw_output),
        path=path,
        raw_output=raw_output,
    )


def explain_node(node: str, graph_json_path: str | os.PathLike[str]) -> str:
    """Explain a graph node using Graphify's deterministic traversal."""
    return _run_graphify(
        ["explain", node, "--graph", str(Path(graph_json_path).resolve())]
    )


def affected_nodes(node: str, graph_json_path: str | os.PathLike[str]) -> str:
    """Find reverse dependents of a node using Graphify."""
    return _run_graphify(
        ["affected", node, "--graph", str(Path(graph_json_path).resolve())]
    )


# Explicit aliases keep the public API discoverable for callers that prefer
# operation-oriented names.
run_update = update_graph
run_query = query_graph
run_path = trace_path
run_explain = explain_node
run_affected = affected_nodes


def load_graph_metrics(
    graph_json_path: str | os.PathLike[str] = DEFAULT_GRAPH_PATH,
) -> GraphMetrics:
    """Load graph JSON and calculate structural metrics and token savings."""
    graph_path = Path(graph_json_path).resolve()
    if not graph_path.is_file():
        raise FileNotFoundError(f"Graph JSON does not exist: {graph_path}")

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = _as_records(graph.get("nodes", []))
    edges = _as_records(graph.get("edges", graph.get("links", [])))
    labels = sorted(
        {
            str(label)
            for node in nodes
            for label in [_node_label(node)]
            if label
        }
    )

    extracted_edges = sum(
        _edge_confidence(edge).upper() == "EXTRACTED" for edge in edges
    )
    inferred_edges = sum(
        _edge_confidence(edge).upper() == "INFERRED" for edge in edges
    )
    raw_tokens = _estimate_raw_source_tokens(graph_path.parent.parent)
    graph_tokens = _estimate_tokens(graph_path.read_text(encoding="utf-8"))
    savings = max(raw_tokens - graph_tokens, 0)
    savings_percent = (savings / raw_tokens * 100) if raw_tokens else 0.0

    return GraphMetrics(
        node_labels=labels,
        total_nodes=len(nodes),
        total_edges=len(edges),
        extracted_edges=int(extracted_edges),
        inferred_edges=int(inferred_edges),
        raw_grep_tokens=raw_tokens,
        graph_tokens=graph_tokens,
        estimated_token_savings=savings,
        estimated_token_savings_percent=round(savings_percent, 2),
    )


parse_graph_metrics = load_graph_metrics


def _as_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [
            dict(item, id=key) if isinstance(item, dict) else {"id": key, "value": item}
            for key, item in value.items()
        ]
    return []


def _node_label(node: dict[str, Any]) -> str:
    for key in ("label", "name", "title", "id"):
        value = node.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _edge_confidence(edge: dict[str, Any]) -> str:
    for source in (
        edge,
        edge.get("metadata"),
        edge.get("attrs"),
        edge.get("data"),
    ):
        if isinstance(source, dict) and source.get("confidence") is not None:
            return str(source["confidence"])
    return ""


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / 4)) if text else 0


def _estimate_raw_source_tokens(scan_root: Path) -> int:
    total_characters = 0
    if not scan_root.is_dir():
        return 0
    for source_path in scan_root.rglob("*.py"):
        if "graphify-out" in source_path.parts or "__pycache__" in source_path.parts:
            continue
        total_characters += len(
            source_path.read_text(encoding="utf-8", errors="replace")
        )
    return _estimate_tokens("x" * total_characters)


def _looks_like_no_path(output: str) -> bool:
    lowered = output.lower()
    return any(phrase in lowered for phrase in ("no path", "not found", "unreachable"))


def _parse_path(output: str) -> list[str]:
    """Extract a readable node sequence from common Graphify path formats."""
    for line in output.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if ":" in candidate and candidate.lower().startswith("path"):
            candidate = candidate.split(":", 1)[1].strip()
        if " -> " in candidate:
            return [part.strip() for part in candidate.split(" -> ") if part.strip()]
        if "→" in candidate:
            return [part.strip() for part in candidate.split("→") if part.strip()]
    return []
