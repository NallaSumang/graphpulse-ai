# GraphPulse

GraphPulse is an open-source codebase knowledge graph and pull-request
blast-radius auditor. It combines Graphify's deterministic structural
extraction with a dual-runtime Gemma 4 auditor so teams can inspect dependency
topology locally, then ask architectural questions using either Google AI
Studio or an offline Ollama model.

## Architecture

```text
                         Python source files
                                  |
                                  v
                    +---------------------------+
                    | Graphify + Tree-sitter AST |
                    | classes, functions, imports|
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | Normalized knowledge graph |
                    | nodes + typed relationships|
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | Leiden community detection |
                    | bounded architectural areas|
                    +-------------+-------------+
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
          EXTRACTED edges              INFERRED edges
       deterministic AST evidence     Graphify-derived relationships
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | GraphPulse engine.py       |
                    | metrics, path, explain,   |
                    | affected, query, update    |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | Gemma 4 Blast-Radius       |
                    | Auditor                    |
                    |                            |
                    | Google AI Studio           |
                    | gemma-4-26b-a4b-it         |
                    |          or                |
                    | Local Ollama               |
                    | gemma4:e4b                 |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | Streamlit dashboard        |
                    | topology, AST queries,     |
                    | multimodal PR audit        |
                    +---------------------------+
```

### Edge provenance

- **EXTRACTED** edges are deterministic relationships recovered from source
  structure, such as imports, inheritance, and calls.
- **INFERRED** edges are higher-level relationships derived by Graphify from
  the extracted graph. They are useful for exploration, but should be treated
  as hypotheses during an audit.
- Leiden communities group tightly connected nodes into architectural areas,
  making cross-module blast radius easier to inspect than a flat dependency
  list.

## Token-efficiency benchmark

The following baseline is measured from the generated six-module
`demo_codebase` graph loaded by `engine.load_graph_metrics()`. The raw grep
estimate counts the Python source corpus; the graph estimate counts the
serialized Graphify JSON used by the current conservative comparison. Because
the serialized graph includes labels, metadata, and provenance, this baseline
does not claim savings where the measured representation is larger.

| Metric | Demo baseline |
| --- | ---: |
| AST nodes | 152 |
| Total graph edges | 309 |
| EXTRACTED edges | 259 |
| INFERRED edges | 50 |
| Raw source grep estimate | 4,053 tokens |
| Serialized graph estimate | 30,160 tokens |
| Conservative estimated token savings | 0% |

The important operational efficiency comes from bounded graph traversal:
`path`, `explain`, `affected`, and `query` can retrieve a focused neighborhood
instead of sending an entire repository to an auditor. Future benchmark runs
should record the exact traversal budget and compare that selected context
against the raw source baseline.

## Quickstart

### Local development

PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\venv\Scripts\graphify.exe demo_codebase
.\venv\Scripts\streamlit.exe run app.py
```

Open the dashboard at <http://localhost:8501>.

The generated graph outputs are written to:

```text
demo_codebase/graphify-out/
  graph.json
  GRAPH_REPORT.md
  graph.html
```

### Deterministic Graphify operations

```powershell
# Incrementally update the graph
.\venv\Scripts\graphify.exe update demo_codebase

# Explore the generated graph
.\venv\Scripts\graphify.exe query "What calls the payment gateway?" --graph demo_codebase\graphify-out\graph.json
.\venv\Scripts\graphify.exe path Customer PaymentRouter --graph demo_codebase\graphify-out\graph.json
.\venv\Scripts\graphify.exe explain RiskEngine --graph demo_codebase\graphify-out\graph.json
.\venv\Scripts\graphify.exe affected Customer --graph demo_codebase\graphify-out\graph.json
```

### Gemma 4 runtimes

Select the runtime in the Streamlit sidebar:

1. **Gemini API** — enter `GEMINI_API_KEY` and use
   `gemma-4-26b-a4b-it`.
2. **Local Ollama** — run Ollama locally with the `gemma4:e4b` model. No
   external API key is required.

```powershell
ollama pull gemma4:e4b
ollama serve
```

The auditor combines `GRAPH_REPORT.md`, graph nodes and edges, and an optional
PNG/JPG cluster screenshot into a structured report covering severity,
downstream modules, God Node bottlenecks, and decoupling steps.

## Docker / Cloudways

The root [Dockerfile](./Dockerfile) uses
`python:3.11-slim`, installs [requirements.txt](./requirements.txt),
and serves Streamlit on port `8501`.

```powershell
docker build -t graphpulse .
docker run --rm -p 8501:8501 graphpulse
```

For Cloudways, deploy the image or its generated container configuration and
route the public application port to container port `8501`.

## Project layout

```text
.
├── app.py                 # Streamlit dashboard
├── engine.py              # Graphify subprocess and metrics layer
├── gemma_auditor.py       # Gemini/Ollama audit service
├── test_engine.py         # focused engine tests
├── demo_codebase/         # synthetic multi-module audit fixture
│   ├── *.py
│   └── graphify-out/      # generated graph, report, and HTML
├── requirements.txt
└── Dockerfile
```

Run the focused tests with:

```powershell
.\venv\Scripts\python.exe -m pytest -q test_engine.py
```