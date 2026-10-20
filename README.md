# ⚡ RepoGraph

> **Zero-Read Codebase Onboarding via Local AST + Open-Weight LLMs.**  
> *Built for the Dev.to Hacktoberfest Open-Source AI Challenge (Theme: Slow and Steady / Sloth).*

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/pip%20dependencies-0-success.svg)](repograph.py)
[![Privacy](https://img.shields.io/badge/privacy-100%25%20Air--Gapped-purple.svg)](repograph.py)
[![Offline AI](https://img.shields.io/badge/Ollama-Offline%20First-orange.svg)](https://ollama.com)
[![Live Demo](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-22c55e.svg)](https://sharan-s-dev.github.io/RepoGraph-/)

Software engineers spend up to 70% of their onboarding time reading through spaghetti code.  
**RepoGraph rewards pure laziness:** clone any repository, run one terminal command, and immediately get an interactive, pan-and-zoom architectural blueprint without reading a single line of source code.

👉 **[Launch Live Interactive Web App on GitHub Pages](https://sharan-s-dev.github.io/RepoGraph-/)**

---

## 🏗️ How It Works (The Zero-Lag Hybrid Architecture)

Most AI code visualizers fail because they dump thousands of raw lines into an LLM context window, causing token limits, high latency, and hallucinations. 

```
                                  ┌───────────────────────────┐
                                  │   Target Python Repo      │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │   Python Native AST Engine │  < 0.1s (100% Deterministic)
                                  │   - Classes & Methods     │
                                  │   - Public Functions      │
                                  │   - Import Topologies     │
                                  └─────────────┬─────────────┘
                                                │ Compact JSON Topology (~200 tokens)
                                                ▼
                     ┌─────────────────────────────────────────────────────┐
                     │           Local LLM Inference (Ollama)              │
                     │  - Models: llama3.2:3b, qwen2.5-coder, gemma2       │
                     │  - Architectural Clustering & Subgraph Layering     │
                     └──────────────────────────┬──────────────────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     │                                                     │
                     ▼                                                     ▼
        ┌─────────────────────────┐                           ┌─────────────────────────┐
        │     ARCHITECTURE.md     │                           │      index.html         │
        │ Native GitHub Markdown  │                           │ Interactive Web App UI  │
        │     Mermaid Diagram     │                           │ Pan/Zoom + Deep Inspect │
        └─────────────────────────┘                           └─────────────────────────┘
```

**RepoGraph takes a deterministic-first approach:**
1. **Python AST Engine (< 0.1s):** Uses Python's native `ast` module to extract classes, functions, and cross-module internal dependencies with 100% mathematical accuracy. Zero third-party `pip` dependencies.
2. **Local Open-Weight Model (Ollama):** Receives a clean, structured JSON topology (~200 tokens) to group components into architectural subgraphs (*Application Entry, Core Logic, API Layer, Data Access, Utilities*).
3. **Bulletproof Fallback Engine:** If Ollama is offline or returns an invalid syntax, RepoGraph automatically switches to its deterministic AST layer clustering with zero downtime.
4. **Interactive Web Workspace:** Generates a standalone, dark-mode `index.html` dashboard powered by `svg-pan-zoom` and Mermaid.js, complete with an in-browser Python folder parser, interactive module inspector drawer, and 30-second lazy onboarding guide.

---

## 🛡️ Why Open Innovation Matters Here

* **100% Air-Gapped & Private:** Proprietary codebases cannot be uploaded to closed cloud APIs (like OpenAI or Anthropic) due to enterprise NDAs, privacy policies, and intellectual property constraints. RepoGraph runs 100% locally on your machine.
* **$0 Infinite Inference:** Analyze codebases of any size with zero API bills, rate limits, or monthly SaaS subscriptions.
* **Works Offline & on GitHub Pages:** Inspect repositories locally without internet, or access the live web app deployed on GitHub Pages.
* **Platform Resilient:** Built and audited to eliminate path separator crashes on Windows (`.as_posix()`), Unicode encoding errors on Windows command prompts, and Mermaid diagram syntax breaks.

---

## ⚡ Quickstart

### Option A: Use the Web Interface (Zero Install)
Visit the live GitHub Pages app:  
🌐 **[https://sharan-s-dev.github.io/RepoGraph-/](https://sharan-s-dev.github.io/RepoGraph-/)**  
Click **"📂 Open Local Repo"** or drag & drop any Python project folder right into the browser!

### Option B: Run Locally via Python CLI
```bash
# Analyze any local repository or directory
python repograph.py demo_project

# Launch the live local server:
python repograph.py demo_project --serve
```

---

## 🎯 Production-Grade Audit & Reliability Fixes

RepoGraph was specifically battle-tested to eliminate the 4 most common failure points that break student and hackathon visualizers:

| Failure Point | Why Other Tools Crash | RepoGraph Battle-Tested Solution |
| :--- | :--- | :--- |
| **Path Separators** | Windows backslashes (`\`) break graph node IDs and syntax | Uses `Path.as_posix()` normalized relative paths across all operating systems |
| **Mermaid Syntax** | Dashes, slashes, and dots trigger red `Syntax error in graph` popups | Alphanumeric sanitization (`sanitize_id`) guarantees bulletproof Mermaid node IDs |
| **Pan & Zoom Clipping** | Repos with >5 files clip off-screen and become unreadable | Integrated dynamic `svg-pan-zoom` with custom floating HUD (Zoom, Reset, Fit) |
| **Missing AI Models** | Hardcoded model strings crash if the user doesn't have that model | Auto-queries Ollama's local tags (`/api/tags`) to detect whatever model is installed |
| **Windows Console CP1252** | Emoji prints trigger `UnicodeEncodeError: 'charmap'` on Windows CMD | Automatic UTF-8 stream reconfiguration on Windows consoles |

---

## 🦥 The "Sloth" Features (Zero-Read Onboarding)

* **30-Second Lazy Guide Modal:** Identifies where execution begins, which files contain the core business algorithms, and how to extend the codebase without reading raw source code.
* **Interactive Module Inspector:** Click any node in the graph or sidebar to see lines of code (LOC), complexity rank, class method signatures, and direct inbound/outbound dependencies.
* **Architecture Layer Filtering:** Filter by layer (*Application Entry, Core & Domain, API & Interface, Data & Storage, Utilities*).
* **One-Click Exports:** Copy Mermaid code directly to your clipboard or download `ARCHITECTURE.md` and SVG vector diagrams.

---

## 📄 License

MIT License. Free and open source for everyone.