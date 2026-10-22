---
title: RepoGraph: Sub-0.1s Codebase Architecture Explorer Powered by Google Gemma
published: true
tags: hf26challenge, gemma, python, architecture, ai
canonical_url: https://github.com/sharan-s-dev/RepoGraph-
cover_image: https://raw.githubusercontent.com/sharan-s-dev/RepoGraph-/main/index.html
---

> *Submission for the **Hacktoberfest Open-Source AI Challenge: Week 3 (Slow and Steady / Sloth Edition)** in the **Best Use of Gemma** category.*

---

## 🦥 The "Sloth Developer" Problem: Understanding Legacy Codebases

Software engineers are famously passionate about **working smart instead of working hard**. But there is one task every developer dreads: being dropped into an unfamiliar, 50-file legacy Python repository without architectural documentation and being told: *"Figure out how this works."*

Normally, you spend hours:
- Clicking through dozens of nested directories,
- Tracing obscure import statements across packages,
- Manually drawing box-and-arrow diagrams on whiteboards,
- Getting bit by nasty runtime `ImportError: cannot import name ... from partially initialized module` circular import bugs.

This is tedious cognitive labor. In the spirit of International Sloth Day, why spend mental energy deciphering spaghetti architecture when we can let open-source AI and deterministic compilers do the heavy lifting for us?

Meet **RepoGraph** — a sub-0.1-second deterministic Python architecture scanner coupled with an **open-weight Google Gemma 2 AI architect engine**.

With a single terminal command:
```bash
python repograph.py ./my-project
```
RepoGraph deterministically parses your code's Abstract Syntax Tree (AST), clusters your modules into architectural tiers, feeds the topology to **Google Gemma**, and produces an interactive, zoomable blueprint in your browser with circular dependency refactoring recipes.

🌐 **[Try the Live Web Demo (GitHub Pages)](https://sharan-s-dev.github.io/RepoGraph-/)**  
📦 **[GitHub Repository](https://github.com/sharan-s-dev/RepoGraph-)**

---

## 💡 Why Open Innovation Matters for What You Built

> **Judges Prompt Response: Why Open Innovation Matters for What You Built**

When designing AI developer tooling, the default instinct for many is to pipe code into a closed cloud LLM API (like OpenAI or Claude). For RepoGraph, **closed AI was a complete non-starter**. Open innovation through **Google's open-weight Gemma family** was the foundational architectural decision for three critical reasons:

### 1. Absolute Data Sovereignty & IP Privacy
Private repositories, fintech codebases, healthcare backends, and proprietary algorithms **cannot leave developer machines**. Enterprise compliance (SOC2, HIPAA, GDPR) strictly prohibits exfiltrating unreleased source code to closed corporate cloud APIs where data might be retained, logged, or used for model training.

Because **Gemma 2 (`gemma2:2b`, `gemma2:9b`) is fully open-weight**, developers can run it 100% locally on their own laptop or air-gapped workstations using Ollama or llama.cpp. Not a single line of proprietary source code ever crosses the network boundary.

### 2. Zero Token Costs & Zero Rate Limits
Closed APIs charge per token. A developer analyzing large repositories with dozens of modules repeatedly during daily refactoring cycles would quickly accumulate non-trivial API bills and hit rate limits. 

With open-weight Gemma, the marginal cost of running architectural analysis is **$0.00**. You can analyze 100 codebases a day without an API key, without a credit card, and without an internet connection.

### 3. Open Hybrid Pipeline: Determinism + Generative Reasoning
Closed LLMs hallucinate dependencies, miss edge cases, and take 10+ seconds to process raw files. 

Open innovation allowed us to construct a **hybrid two-tier architecture**:
- **Tier 1 (Compiler Speed):** Python's open standard library `ast` parses class hierarchies, method signatures, and imports deterministically in **< 0.05 seconds**.
- **Tier 2 (Open-Weight Reasoning):** Google's lightweight `gemma2:2b` digests the extracted semantic structure to identify design patterns, calculate architectural health scores, and write refactoring recipes.

If the developer is offline on an airplane without an active local AI daemon, RepoGraph's built-in offline synthesis engine kicks in gracefully. The tool *never* fails.

---

## 🏗️ Architecture Pipeline

RepoGraph operates as an end-to-end, zero-dependency pipeline:

```
┌─────────────────────────────────┐
│       Target Python Repo        │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Python Native AST Engine    │  < 0.1s execution (Zero external pip deps)
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
│  - Cycle Detection (Tarjan DFS) │
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

## 🤖 Inside the Gemma AI Architect Engine

RepoGraph leverages Google's **Gemma 2** to turn dry dependency lists into deep architectural intelligence:

### 1. Executive Architectural Narrative
Instead of reading 20 files, Gemma synthesizes a concise executive summary explaining the primary purpose, responsibilities, and structural boundaries of the codebase.

### 2. Design Pattern Detection
Gemma analyzes the relationship graph and class naming conventions to automatically flag architectural design patterns:
- **Clean N-Tier Layered Architecture** (Interface ➔ Core ➔ Storage separation)
- **Dispatcher & Facade Pattern** (Centralized routing layers)
- **Core Domain Workflow Orchestrator** (Stateful business logic coordinators)
- **Data Entity & Domain Model** (Structured persistence entities)
- **Stateless Shared Service Provider** (Cryptographic and string utilities)

### 3. Actionable Circular Dependency Refactoring Recipes
When cyclic imports are detected (`routes.py ➔ engine.py ➔ routes.py`), RepoGraph doesn't just display an error. Gemma provides a concrete, 3-step refactoring recipe based on the **Dependency Inversion Principle (DIP)**:
1. Extract shared interfaces or DTOs into a dedicated module,
2. Invert dependencies so high-level modules depend on abstractions,
3. Eliminate runtime import hazards.

### 4. Per-Module Role Explanations in the Inspector Drawer
Clicking on any file in the interactive web canvas opens an inspector drawer where Gemma provides a dedicated synopsis of that specific module's architectural role within the larger system.

---

## 🎨 Interactive Blueprint Highlights

The generated `index.html` is a standalone, self-contained single-page application with zero third-party JavaScript dependencies:

- **Infinite Vector Canvas:** Smooth drag-to-pan, scroll-to-zoom, and mobile touch pinch-to-zoom using a custom SVG transform matrix engine.
- **Bidirectional Pathway Lighting:** Click any module to illuminate callers in **emerald green** and dependencies in **cyan**, with glowing vector edges while dimming unrelated code.
- **Circular Dependency Radar:** Cycles are highlighted in vivid crimson, with direct links in the top navigation modal.
- **Orientation Switcher (<kbd>T</kbd>):** Instantly toggle between Top-Down (TD) and Left-to-Right (LR) layouts.
- **Gemma Modal (<kbd>G</kbd> or <kbd>A</kbd>):** Dedicated full-screen modal showing the Gemma AI report, health score, detected patterns, and actionable recommendations.
- **Multi-Format Exports:** Export vector SVG (with embedded styling for Figma/draw.io), Mermaid Markdown, or auto-generated `ARCHITECTURE.md`.

---

## 🚀 How to Run RepoGraph in 10 Seconds

RepoGraph requires **zero external pip dependencies**. All you need is Python 3.9+:

### Step 1: Clone and Run
```bash
git clone https://github.com/sharan-s-dev/RepoGraph-.git
cd RepoGraph-

# Analyze any local repo
python repograph.py ./my-project --serve
```

### Step 2: Use Local Gemma with Ollama (Optional)
If you have [Ollama](https://ollama.ai) installed:
```bash
ollama run gemma2:2b
python repograph.py ./my-project --ai-provider ollama
```
RepoGraph will automatically detect your local Gemma runner on port `11434` and execute live local inference!

---

## 🧪 Rigorous Engineering & Unit Testing

RepoGraph includes a comprehensive multi-platform unit test suite tested on Windows, macOS, and Linux:
- `ast` visitor signature extraction
- Subpackage and multi-root import resolution across `src/` and nested directories
- Circular dependency cycle detection (Tarjan DFS)
- Gemma AI Architect prompt generation, pattern synthesis, and cycle remediation recipes
- Resilient HTML generation

```bash
python -m unittest discover tests
# Ran 21 tests in 0.525s - OK!
```

---

## 🏁 Summary

The DEV.to Hacktoberfest "Slow and Steady" challenge reminded us that the best developers aren't the ones who grind through manual boilerplate — they're the ones who automate the friction away.

By combining the **sub-0.1s mathematical precision of native AST parsing** with the **open-weight reasoning of Google's Gemma 2**, RepoGraph lets developers offload codebase archaeology and get straight to building.

- 🌐 **Live Demo:** [https://sharan-s-dev.github.io/RepoGraph-/](https://sharan-s-dev.github.io/RepoGraph-/)
- 💻 **Source Code:** [https://github.com/sharan-s-dev/RepoGraph-](https://github.com/sharan-s-dev/RepoGraph-)
- 📜 **License:** MIT Open Source

*Built with ❤️ for Hacktoberfest 2026.*
