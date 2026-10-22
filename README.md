# RepoGraph

> **Fast, deterministic codebase architecture & dependency graph explorer for Python.**

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external-success.svg)](repograph.py)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](repograph.py)
[![Live Demo](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-22c55e.svg)](https://sharan-s-dev.github.io/RepoGraph-/)

RepoGraph scans any Python codebase using Python's native Abstract Syntax Tree (AST) engine in under 0.1s and produces an interactive, zoomable architectural blueprint with deep dependency inspection.

🌐 **[Open Live Web Interface](https://sharan-s-dev.github.io/RepoGraph-/)**

---

## Architecture Pipeline

```
┌─────────────────────────┐
│   Target Python Repo    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Python Native AST Engine│  < 0.1s execution (Zero dependencies)
│ - Class hierarchies     │
│ - Public functions      │
│ - Relative/abs imports  │
│ - Cyclomatic complexity │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Architectural Grouping  │  Deterministic layer clustering
│ - Application Entry     │  (Entry, API, Core, Data, Utils, Config)
│ - Domain Boundaries     │
└────────────┬────────────┘
             │
     ┌───────┴───────┐
     │               │
     ▼               ▼
┌──────────────┐ ┌──────────────────────────────────────┐
│ARCHITECTURE.md│ │ index.html & repograph.html           │
│Mermaid GitHub│ │ Interactive Canvas (Pan, Zoom, Trace)│
└──────────────┘ └──────────────────────────────────────┘
```

---

## Features

- **Sub-0.1s Deterministic Parsing:** Uses Python's native `ast` module. Extracts class definitions, base classes, methods with parameter signatures, and cross-module import paths with mathematical accuracy.
- **Interactive Canvas with Native Pan & Zoom:** Custom zero-dependency transform engine that never clips or collapses. Smooth mouse drag, scroll wheel zoom, and mobile touch pinch-to-zoom.
- **True Bidirectional Pathway Lighting:** Click any module in the graph or sidebar to illuminate inbound callers (emerald green) and outbound dependencies (cyan), with matching glowing edge paths while dimming unrelated code.
- **Circular Dependency Detection:** Automatically detects cyclic import chains (`A ➔ B ➔ A`), alerts in the terminal, displays an in-app banner/modal, and highlights the cycle in vivid crimson on the diagram.
- **Deep Codebase Inspector:** Slide-out drawer displaying module docstrings, lines of code (LOC), branch complexity ratings, class hierarchies with base classes and public methods, clickable internal dependency links, and external / standard library dependencies.
- **Layer Filtering & Instant Search:** Filter by architectural layer (*Application Entry, API, Core, Data, Utilities, Config*) or search classes and functions with instant diagram highlighting.
- **Multi-Format Exports:** One-click export to vector SVG (with embedded fonts and styling), Mermaid Markdown, and GitHub-ready `ARCHITECTURE.md`.
- **Zero Third-Party Dependencies:** Standard library only (`ast`, `argparse`, `json`, `os`, `re`, `sys`, `pathlib`). No `pip install` required.

---

## Quickstart

### 1. Run Analysis on Any Repository
```bash
# Analyze a specific directory
python repograph.py ./my-project

# Or analyze the current folder
python repograph.py .

# Output to a custom directory without clobbering local files
python repograph.py ./my-project -o ./docs

# Custom project name
python repograph.py ./my-project --name "AcmeBackend"
```

### 2. Output Artifacts Generated
- **`index.html` & `repograph.html`:** Self-contained interactive web dashboards. Double-click to open in any browser.
- **`ARCHITECTURE.md`:** Valid Mermaid markdown diagram that renders natively inside GitHub READMEs and wikis (annotated with circular dependency alerts if detected).

### 3. Launch Built-in Local Server (Optional)
```bash
python repograph.py ./my-project --serve --port 8080
```
Starts a lightweight local HTTP server at `http://localhost:8080/index.html` and automatically opens your browser.

### 4. CLI Options
```
repograph [-h] [-o OUTPUT] [--name NAME] [--serve] [--port PORT]
          [--no-browser] [--json] [--exclude [EXCLUDE ...]] [--no-html]
          [target]

options:
  -h, --help            Show help message and exit
  -o, --output OUTPUT   Output directory to place generated files
  --name NAME           Custom project name (overrides auto-detection)
  --serve               Launch local HTTP server and open blueprint in browser
  --port PORT           Port for HTTP server (default: 8080)
  --no-browser          Do not automatically open browser when serving
  --json                Output raw codebase summary as JSON to stdout
  --exclude EXCLUDE     Additional directories or files to ignore
  --no-html             Skip HTML generation (only generate ARCHITECTURE.md)
```

---

## Running Tests

Run the built-in unit test suite (zero external test dependencies required):
```bash
python -m unittest discover tests
```

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