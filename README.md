# RepoGraph — Deterministic Codebase Intelligence

> **Turn an unfamiliar Python repository into an inspectable architecture map in seconds.**

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-Google%20Gemma%202%20(Open--Weight)-8b5cf6.svg)](repograph.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CLI Dependencies](https://img.shields.io/badge/CLI%20dependencies-0-success.svg)](repograph.py)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](repograph.py)
[![Live Demo](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-22c55e.svg)](https://sharan-s-dev.github.io/RepoGraph-/)
[![Hacktoberfest 2026](https://img.shields.io/badge/Hacktoberfest-2026%20Contender-f97316.svg)](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)

RepoGraph scans a Python codebase with the standard-library AST engine, produces a deterministic dependency graph and explainable metrics, then optionally asks a local open-weight model for architectural commentary. The factual graph never depends on an LLM. If no model is available, the report still works through deterministic synthesis.

🌐 **[Open Live Web Interface](https://sharan-s-dev.github.io/RepoGraph-/)**

---

## Architecture Pipeline

```
┌─────────────────────────────────┐
│       Target Python Repo        │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Python Native AST Engine    │  Fast, deterministic (Zero external pip deps)
│  - Class hierarchies & methods  │
│  - Public functions & docstrings│
│  - Relative/subpackage imports  │
│  - Cyclomatic branch complexity │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  Architectural Layer Classifier │  Deterministic layer clustering
│  - Application Entry            │  (Entry, API, Core, Data, Utils, Config)
│  - Domain Boundaries & Cycles   │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Google Gemma 2 AI Architect   │  Open-weight local intelligence
│  - Executive System Narrative   │  (Ollama / llama.cpp / Groq / Offline fallback)
│  - Design Pattern Detection     │  Data Sovereignty: 0 private code leaves your laptop
│  - Cycle Refactoring Recipes    │
│  - Architecture Health Score    │
└────────────────┬────────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
┌────────────────┐ ┌──────────────────────────────────────────┐
│ ARCHITECTURE.md│ │ index.html & repograph.html              │
│ Mermaid GitHub │ │ Interactive Canvas (Pan, Zoom, Highlight)│
│ + Gemma Report │ │ + Interactive Gemma AI Architect Modal   │
└────────────────┘ └──────────────────────────────────────────┘
```

---

### The important boundary

```text
source files ──▶ Python AST ──▶ validated graph + metrics ──▶ HTML / Mermaid / JSON
                                      │
                                      └── optional local model narrative
```

The model can explain the graph; it cannot invent the graph. This separation makes RepoGraph useful for private repositories, reproducible in CI, and testable without model weights.

---

## Why Open Innovation & Open-Weight AI (Gemma)?

When analyzing proprietary or sensitive codebases, developers often cannot send private source code to closed cloud LLM APIs because of IP, compliance, and cost constraints. RepoGraph keeps deterministic analysis local and makes hosted inference an explicit opt-in rather than a hidden default.

RepoGraph solves this through **open innovation with Google Gemma**:
1. **Data sovereignty by default:** Run `gemma2:2b` or `gemma2:9b` locally on your machine via Ollama or llama.cpp. In the default local path, proprietary code never leaves your local network.
2. **Deterministic facts + open-weight reasoning:** AST extracts the factual dependency topology, then the optional model receives a compact semantic summary rather than raw source files.
3. **Resilient Offline Fallback:** Even without an active local AI server running, RepoGraph's built-in synthesis engine produces structured architectural assessments without failing.

---

## Key Features

- **Deterministic AST Parsing:** Uses Python's native `ast` module. Extracts class hierarchies, base classes, method signatures with arguments, docstrings, imports, cycles, and graph metrics without an LLM.
- **🤖 Gemma AI Architectural Intelligence:**
  - **Executive Architecture Narrative:** Synthesizes an executive overview of the project's responsibilities and workflows.
  - **Design Pattern Detection:** Identifies Clean N-Tier Architecture, Dispatcher/Facade, Domain Workflow Orchestrator, Data Entity Model, and Shared Services.
  - **Architectural Health Score:** Rates codebase modularity (A, A-, B, C+) based on coupling density and cyclic hazards.
  - **Actionable Circular Dependency Recipes:** Step-by-step refactoring guidance applying the Dependency Inversion Principle.
  - **Per-Module Architectural Roles:** Inspect any module to see its architectural purpose as understood by Gemma.
- **Interactive Canvas with Native Pan & Zoom:** Custom zero-dependency SVG transform engine that never clips or collapses. Smooth mouse drag, scroll wheel zoom, and mobile touch pinch-to-zoom.
- **True Bidirectional Pathway Lighting:** Click any module in the graph or sidebar to illuminate inbound callers (emerald green) and outbound dependencies (cyan), with matching glowing edge paths while dimming unrelated code.
- **Circular Dependency Detection:** Automatically detects cyclic import chains (`A ➔ B ➔ A`), alerts in the terminal, displays an in-app banner/modal, and highlights the cycle in vivid crimson on the diagram.
- **Deep Codebase Inspector:** Slide-out drawer displaying module docstrings, lines of code (LOC), branch complexity ratings, class hierarchies with base classes and public methods, clickable internal dependency links, and external / standard library dependencies.
- **Layer Filtering & Instant Search:** Filter by architectural layer (*Application Entry, API, Core, Data, Utilities, Config*) or search classes and functions with instant diagram highlighting.
- **Multi-Format Exports:** One-click export to vector SVG (with embedded fonts and styling), Mermaid Markdown, and GitHub-ready `ARCHITECTURE.md`.
- **Zero Python Runtime Dependencies:** Standard library only (`ast`, `argparse`, `json`, `os`, `re`, `sys`, `pathlib`, `socket`, `urllib`). No `pip install` is required for the CLI.

---

## Quickstart

### 1. Run Analysis on Any Repository
```bash
# Analyze a specific directory with Gemma AI enabled (default)
python repograph.py ./my-project

# Analyze current folder
python repograph.py .

# Custom project name
python repograph.py ./my-project --name "AcmeBackend"

# Specify a custom Gemma model or provider
python repograph.py ./my-project --ai-model gemma2:2b --ai-provider ollama
```

### 2. Output Artifacts Generated
- **`index.html` & `repograph.html`:** Interactive dashboards with the Gemma AI Architect modal, Mermaid enhancement, and a built-in SVG fallback when the CDN is unavailable.
- **`ARCHITECTURE.md`:** Valid Mermaid markdown diagram that renders natively inside GitHub READMEs and wikis, complete with the Gemma AI architectural assessment.
- **`--json`:** Stable machine-readable report with `schema_version`, graph metrics, cycles, module records, and parse diagnostics. Progress logs go to stderr so the JSON is safe for pipes and CI.

### 3. Launch Built-in Local Server (Optional)
```bash
python repograph.py ./my-project --serve --port 8080
```
Starts a lightweight local HTTP server at `http://localhost:8080/index.html` and automatically opens your browser.

### 4. CLI Options
```
repograph [-h] [-o OUTPUT] [--name NAME] [--ai] [--no-ai]
          [--ai-model AI_MODEL] [--ai-provider {auto,ollama,local,groq,hf}]
          [--ai-key AI_KEY] [--serve] [--port PORT] [--no-browser]
          [--json] [--exclude [EXCLUDE ...]] [--no-html]
          [target]

options:
  -h, --help            Show this help message and exit
  -o, --output OUTPUT   Output directory to place generated files (default: .)
  --name NAME           Custom project name to display (overrides auto-detection)
  --ai                  Run Google Gemma open-weight AI architecture intelligence (default: True)
  --no-ai               Disable Gemma AI analysis
  --ai-model AI_MODEL   Gemma model identifier (default: gemma2:2b; supports gemma2, gemma2:9b)
  --ai-provider {auto,ollama,local,groq,hf}
                        Inference provider (default: auto; checks local Ollama, llama.cpp, or endpoints)
  --ai-key AI_KEY       API key for hosted Gemma endpoints (optional, or use GROQ_API_KEY env var)
  --serve               Launch local HTTP server and open blueprint in browser
  --port PORT           Port for HTTP server (default: 8080)
  --no-browser          Do not automatically open browser when serving
  --json                Output raw codebase summary as JSON to stdout
  --exclude EXCLUDE     Additional directories or files to ignore
  --no-html             Skip HTML generation (only generate ARCHITECTURE.md)
```

---

## Keyboard Shortcuts in Interactive Blueprint

| Key | Action |
|:---:|:---|
| <kbd>G</kbd> / <kbd>A</kbd> | Open **Gemma AI Architect** Intelligence Modal |
| <kbd>T</kbd> | Toggle Canvas Orientation (Top-to-Bottom ⇄ Left-to-Right) |
| <kbd>F</kbd> | Fit Canvas to Screen |
| <kbd>O</kbd> | Open Architecture Overview & Metrics Modal |
| <kbd>C</kbd> | Open Circular Dependency Inspector (if cycles exist) |
| <kbd>Ctrl</kbd> + <kbd>K</kbd> | Focus Instant Search |
| <kbd>Esc</kbd> | Close any open drawer or modal |

---

## Running Tests

Run the built-in unit test suite (zero external test dependencies required):
```bash
python -m unittest discover -s tests -p "test*.py"
```

The suite covers AST extraction, import resolution, cycle detection, metric contracts, model-output validation, safe HTML embedding, and artifact generation.

---

## Platform Reliability

- **Windows & Unix Path Normalization:** Standardizes on `.as_posix()` to eliminate backslash syntax issues across operating systems.
- **Subpackage & Multi-Root Import Resolution:** Resolves imports across `src/`, nested packages, relative levels (`.`, `..`), and `__init__.py` namespaces without losing dependency edges.
- **Mermaid ID Sanitization:** Strict alphanumeric formatting prevents syntax parsing crashes on special characters.
- **Windows Console UTF-8 Safety:** Reconfigures console streams to avoid `cp1252` encoding errors on Windows command prompts.
- **Self-Contained SVG Export:** Embeds vector font definitions and CSS styles so exported SVGs render identically in vector editors, web pages, and image viewers.

---

## License

MIT License. Free and open source.
