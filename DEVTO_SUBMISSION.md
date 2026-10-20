---
title: Building RepoGraph: A Sub-0.1s Deterministic Codebase Architecture Explorer
published: true
tags: python, architecture, visualization, opensource
canonical_url: https://github.com/sharan-s-dev/RepoGraph-
cover_image: https://raw.githubusercontent.com/sharan-s-dev/RepoGraph-/main/index.html
---

## The Architecture Problem: Mapping Codebases Fast

Whenever engineers clone a complex open-source repository or join a new engineering team, the first few hours are often spent clicking through nested folders, tracing import chains, deciphering inheritance trees, and trying to reconstruct a mental map of what talks to what.

Many modern code visualizers rely on heavy cloud LLMs or third-party graph dependencies. However, piping thousands of lines of raw code to external APIs introduces latency, token costs, hallucinated imports, and potential enterprise privacy concerns.

**RepoGraph** was created to solve this fundamentally using **deterministic Python Abstract Syntax Trees (AST)** paired with an interactive, zero-dependency browser blueprint.

---

## ⚡ What It Does

From any terminal:

```bash
python repograph.py ./my-project
```

In under **0.1 seconds**, with **zero `pip install` dependencies**, RepoGraph:

1. **Scans the AST:** Crawls classes, methods, signatures, docstrings, complexity, and cross-module import paths (including relative depth and `__init__.py` namespaces).
2. **Clusters Architectural Layers:** Automatically classifies modules into structural tiers (*Application Entry, API & Interfaces, Core Domain, Data & Storage, Utilities & Shared, Configuration*).
3. **Generates Blueprints:**
   - **`index.html` & `repograph.html`:** Self-contained dark-mode interactive dashboards with a custom vector pan & zoom engine, orientation toggles (Top-Down ⇄ Left-to-Right), instant symbol search, and dependency pathway lighting.
   - **`ARCHITECTURE.md`:** A clean Mermaid diagram ready to drop into GitHub READMEs and team documentation.

---

## 🏗️ Architecture Pipeline

```
┌─────────────────────────────────┐
│       Target Python Repo        │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Python Native AST Engine    │  < 0.1s execution (Zero external pip deps)
│  - Class hierarchies & bases    │
│  - Method & function signatures │
│  - Relative & package imports   │
│  - Cyclomatic complexity score  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Architectural Clustering    │  Categorizes modules by responsibility
│  - Application Entry            │  (Entry, API, Core, Data, Utils, Config)
│  - Domain Boundaries            │
└────────────────┬────────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
┌────────────────┐ ┌──────────────────────────────────────┐
│ARCHITECTURE.md │ │ index.html & repograph.html           │
│Mermaid Markdown│ │ Interactive Vector Canvas             │
│GitHub Native   │ │ (Pan, Zoom, Trace, Inspect, Exports) │
└────────────────┘ └──────────────────────────────────────┘
```

---

## 🎯 Engineering Highlights & Reliability

Building an architecture visualizer that works reliably across disparate environments requires solving key edge cases:

1. **Cross-Platform Path Normalization:** Windows backslashes (`\`) break graph node identifiers and web URL routing. RepoGraph standardizes on `.as_posix()` throughout the pipeline.
2. **Mermaid Identifier Sanitization:** Special characters (`-`, `.`, `/`, spaces) cause syntax parsing exceptions. Strict alphanumeric normalization guarantees syntax stability.
3. **Zero-Dependency Vector Canvas:** Rather than depending on heavy third-party CDN canvas libraries that can fail during layout reflows, RepoGraph implements a pure CSS transform matrix engine (`translate(x, y) scale(s)`) anchored to mouse cursor coordinates for smooth, infinite vector zooming.
4. **Orientation Toggling (TD ⇄ LR):** Deep hierarchical codebases often read better vertically (Top-Down), while pipelines and data flows read better horizontally (Left-to-Right). RepoGraph embeds both layouts and lets developers toggle views in one click.
5. **Pathway Lighting:** Selecting any node in the graph or sidebar illuminates its inbound callers (emerald green) and outbound dependencies (cyan), while dimming unrelated components.

---

## 🛠️ Open-Source Repository & Live Demo

- **GitHub Repository:** [https://github.com/sharan-s-dev/RepoGraph-](https://github.com/sharan-s-dev/RepoGraph-)
- **Live Interactive Demo:** [https://sharan-s-dev.github.io/RepoGraph-/](https://sharan-s-dev.github.io/RepoGraph-/)
- **License:** MIT License. Free and open source.

