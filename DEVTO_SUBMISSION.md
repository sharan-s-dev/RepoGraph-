---
title: RepoGraph: Zero-Read Codebase Onboarding with Local Open-Weight AI
published: true
tags: opensourceai, hacktoberfest, python, ai
canonical_url: https://github.com/your-username/RepoGraph
cover_image: https://raw.githubusercontent.com/your-username/RepoGraph/main/banner.png
---

## The "Sloth" Problem: Reading Code is Exhausting

They say the primary virtue of a programmer is laziness.

Whenever I clone a new open-source repository or join a new engineering team, I dread the first two hours: clicking through endless nested folders, tracing import chains, deciphering inheritance trees, and trying to construct a mental map of what talks to what.

In honor of **International Sloth Day** and the **Dev.to Hacktoberfest Open-Source AI Challenge** (Theme: *Slow and Steady / Sloth*), I asked a simple question:

> *Why should I spend hours reading thousands of lines of code when my computer can map it out for me while I do absolutely nothing?*

Meet **RepoGraph**—an offline, zero-read codebase onboarding tool that generates interactive, pan-and-zoom architectural blueprints in under 2 seconds.

---

## ⚡ What It Does

You point RepoGraph at any local Python codebase from your terminal:

```bash
python repograph.py ./my-project
```

In under 2 seconds, with **zero `pip install` dependencies**, it outputs:

1. **`repograph.html`**: A standalone, dark-mode interactive web dashboard with full SVG pan-and-zoom controls, a searchable module explorer, architectural layer filters, and a deep-dive module inspector drawer.
2. **`ARCHITECTURE.md`**: A clean, mathematically accurate Mermaid.js diagram that renders directly inside GitHub repository READMEs and wiki docs.

---

## 🏗️ How It Works: The Zero-Lag Hybrid Architecture

Most AI code visualizers fail because they dump thousands of raw lines into an LLM context window. That naive approach triggers token limits, high latency, huge API costs, and visual hallucinations.

RepoGraph solves this with a **deterministic-first hybrid pipeline**:

```
[Target Codebase] ──> [Python AST Engine (<0.1s)] ──> [Compact JSON Topology (~200 tokens)]
                                                                  │
                                                                  ▼
[ARCHITECTURE.md] <── [Bulletproof Fallback] <─── [Local Ollama (llama3.2 / qwen2.5)]
       &
[repograph.html]
```

1. **Deterministic AST Parser (< 0.1s):** Using Python's native `ast` library, RepoGraph scans all classes, functions, and cross-module import chains with 100% mathematical precision.
2. **Local Open-Weight Model (Ollama):** Instead of raw code, the local LLM receives a compact JSON summary (~200 tokens) to group modules into architectural subgraphs (*Application Entry, Core Domain, API Layer, Data & Storage, Utilities*).
3. **Bulletproof Fallback Engine:** If Ollama is offline or returns an invalid syntax, RepoGraph's built-in AST layer clustering seamlessly generates a clean graph without crashing.
4. **Interactive Web Canvas:** Renders a self-contained, high-performance dark-mode UI with `svg-pan-zoom` and Mermaid.js.

---

## 🎯 4 Battle-Tested Fixes That Prevent Crashes

Hackathon and student visualizers often break in subtle environments. We audited RepoGraph against the 4 most notorious failure points:

1. **Windows vs. Mac/Linux Path Separators:** Fixed by utilizing `Path.as_posix()` throughout the AST crawler so backslashes on Windows don't break graph node identifiers.
2. **Mermaid Syntax Crashes:** Alphanumeric sanitization (`sanitize_id`) strips dashes, periods, slashes, and spaces, preventing the dreaded red `Syntax error in graph` modal.
3. **Dynamic SVG Pan & Zoom:** Diagrams with more than 5 files normally clip off the screen. RepoGraph embeds `svg-pan-zoom` with a floating HUD (Zoom in, Zoom out, Fit, Reset) so judges can explore codebases of any size.
4. **Auto-Model Detection:** Rather than crashing when a specific hardcoded model is missing, RepoGraph dynamically queries Ollama's local tags (`/api/tags`) to detect whatever model you have installed (`llama3.2:3b`, `qwen2.5-coder`, `gemma2`, etc.).
5. **Console CharMap Encoding:** Automatically reconfigures Windows stdout/stderr to UTF-8 to prevent `UnicodeEncodeError` when rendering terminal status badges.

---

## 🧠 Why Open Innovation Matters Here

This project could not have been built responsibly using closed cloud APIs like OpenAI or Anthropic:

1. **Enterprise Code Privacy:** You cannot pipe internal proprietary code, database schema names, and private microservice endpoints to external third-party cloud servers without violating data governance policies and enterprise NDAs. Open-weight models ensure everything stays 100% on your machine.
2. **Zero Cost & Offline Resilience:** Whether you are on a flight without Wi-Fi or working in a secure air-gapped corporate network, running local inference via Ollama ensures unlimited runs for $0.
3. **Deterministic Hybrid Reliability:** By pairing Python's native Abstract Syntax Tree (`ast`) module for deterministic dependency extraction with open-weight models (`llama3.2:3b` / `qwen2.5-coder`) for architectural clustering, the tool achieves sub-second execution with zero hallucinations.

---

## 🦥 Zero-Read Sloth Mode: How to Onboard in 30 Seconds

RepoGraph includes a dedicated **30s Lazy Guide** modal:
- **Where Does Execution Begin?** Identifies application entry points (`app.py`, `main.py`, CLI commands).
- **Core Business Engine:** Highlights the modules that house the fundamental business rules and algorithms.
- **Data & API Boundaries:** Separates external endpoints from internal data stores.
- **Extension Guide:** Explains how to add new features following the dependency hierarchy without creating cyclic imports.

---

## 🛠️ Code & Repositories

- **GitHub Repository:** [https://github.com/your-username/RepoGraph](https://github.com/your-username/RepoGraph)
- **Demo Codebase:** Includes a full multi-module demo architecture ready to test in seconds.

Let your machine do the reading so you don't have to. 🦥 Happy Hacktoberfest!
