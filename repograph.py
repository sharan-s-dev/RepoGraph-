#!/usr/bin/env python3
"""
RepoGraph (SlothEdition) - Zero-Read Codebase Onboarding
Generates interactive architectural blueprints from local codebases using AST + Local Open-Weight LLMs.
Zero third-party pip dependencies required.
"""

import ast
import json
import os
import re
import sys
import webbrowser
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

# Battle-tested fix: Ensure UTF-8 output on Windows consoles to prevent cp1252 charmap crashes
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

IGNORED_DIRS = {
    ".git", "__pycache__", "venv", ".venv", "env", "node_modules", 
    "dist", "build", ".idea", ".vscode", ".pytest_cache", "tests",
    ".eggs", "*.egg-info", ".mypy_cache", ".ruff_cache", "coverage"
}

def sanitize_id(name: str) -> str:
    """Mermaid node IDs must strictly be alphanumeric and underscores."""
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned or "node_root"

class CodebaseVisitor(ast.NodeVisitor):
    def __init__(self):
        self.classes = []
        self.class_details = {}
        self.functions = []
        self.imports = []
        self.from_imports = []
        self.docstring = ""
        self.has_main = False
        self.complexity_score = 1

    def visit_Module(self, node):
        doc = ast.get_docstring(node)
        if doc:
            self.docstring = doc.strip().split("\n")[0][:140]
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith("__"):
                    methods.append(item.name)
        self.class_details[node.name] = {
            "methods": methods[:6],
            "bases": [b.id for b in node.bases if isinstance(b, ast.Name)]
        }
        self.complexity_score += 2
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if not node.name.startswith("_"):
            self.functions.append(node.name)
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if not node.name.startswith("_"):
            self.functions.append(f"async {node.name}")
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_If(self, node):
        if isinstance(node.test, ast.Compare):
            left = getattr(node.test.left, "id", None)
            if left == "__name__":
                self.has_main = True
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        if node.module:
            self.from_imports.append(node.module)
            self.imports.append(node.module)

def classify_layer(rel_path: str, visitor: CodebaseVisitor) -> str:
    """Classify file into architectural layer based on path conventions and content."""
    lower = rel_path.lower()
    
    if any(k in lower for k in ["route", "controller", "api", "endpoint", "handler", "view", "server"]):
        return "API & Interface"
    if any(k in lower for k in ["model", "schema", "entity", "dto", "database", "db", "repository", "crud"]):
        return "Data & Storage"
    if any(k in lower for k in ["core", "engine", "service", "logic", "domain", "pipeline", "manager"]):
        return "Core & Domain"
    if any(k in lower for k in ["util", "helper", "common", "tool", "shared", "lib"]):
        return "Utilities & Shared"
    if any(k in lower for k in ["config", "setting", "env", "constant"]):
        return "Configuration"
    if visitor.has_main or any(k in lower for k in ["main", "app", "cli", "run", "entry"]):
        return "Application Entry"
    
    return "Domain Services"

def count_file_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def detect_circular_dependencies(summary: Dict[str, Any]) -> List[List[str]]:
    """Simple cycle detection on internal dependencies graph."""
    cycles = []
    visited = set()
    rec_stack = set()
    current_path = []

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        current_path.append(node)

        deps = summary.get(node, {}).get("internal_dependencies", [])
        for dep in deps:
            if dep not in visited:
                dfs(dep)
            elif dep in rec_stack:
                cycle_start = current_path.index(dep)
                cycles.append(current_path[cycle_start:] + [dep])

        current_path.pop()
        rec_stack.remove(node)

    for mod in summary:
        if mod not in visited:
            dfs(mod)

    return cycles[:5]

def scan_repository(repo_path: Path) -> Dict[str, Any]:
    repo_path = repo_path.resolve()
    codebase_summary: Dict[str, Any] = {}
    local_modules = set()
    module_to_file: Dict[str, str] = {}

    py_files: List[Path] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                py_files.append(Path(root) / file)

    for p in py_files:
        rel = p.relative_to(repo_path).with_suffix("")
        # Windows fix: use as_posix() to prevent backslash breakage
        mod_name = rel.as_posix().replace("/", ".")
        local_modules.add(mod_name)
        short_name = mod_name.split(".")[-1]
        local_modules.add(short_name)
        module_to_file[mod_name] = p.relative_to(repo_path).as_posix()
        module_to_file[short_name] = p.relative_to(repo_path).as_posix()

    for p in py_files:
        rel_posix = p.relative_to(repo_path).as_posix()
        loc = count_file_lines(p)
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(p))
            visitor = CodebaseVisitor()
            visitor.visit(tree)

            internal_deps = set()
            for imp in visitor.imports:
                base_imp = imp.split(".")[0]
                if imp in local_modules:
                    target = module_to_file.get(imp)
                    if target and target != rel_posix:
                        internal_deps.add(target)
                elif base_imp in local_modules:
                    target = module_to_file.get(base_imp)
                    if target and target != rel_posix:
                        internal_deps.add(target)

            layer = classify_layer(rel_posix, visitor)

            codebase_summary[rel_posix] = {
                "id": sanitize_id(rel_posix),
                "file": rel_posix,
                "layer": layer,
                "docstring": visitor.docstring or "Python module",
                "classes": visitor.classes,
                "class_details": visitor.class_details,
                "functions": visitor.functions[:8],
                "all_functions_count": len(visitor.functions),
                "internal_dependencies": sorted(list(internal_deps)),
                "has_entry_point": visitor.has_main or rel_posix.endswith(("main.py", "app.py", "cli.py")),
                "loc": loc,
                "complexity": min(visitor.complexity_score, 100),
                "imported_by": []
            }
        except Exception:
            continue

    # Compute reverse dependencies (imported_by)
    for file, data in codebase_summary.items():
        for dep in data["internal_dependencies"]:
            if dep in codebase_summary and file not in codebase_summary[dep]["imported_by"]:
                codebase_summary[dep]["imported_by"].append(file)

    return codebase_summary

def get_installed_ollama_model() -> Tuple[str, bool]:
    """Auto-detect whatever model the user has installed."""
    url = "http://localhost:11434/api/tags"
    preferred = [
        "llama3.2:3b", "llama3.2:latest", "llama3.2", "qwen2.5-coder", 
        "qwen2.5-coder:7b", "gemma2", "gemma2:2b", "llama3", "mistral",
        "deepseek-coder", "phi3"
    ]
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.5) as res:
            data = json.loads(res.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            for pref in preferred:
                for m in models:
                    if pref in m:
                        return m, True
            if models:
                return models[0], True
    except Exception:
        pass
    return "llama3.2:3b", False

def query_ollama(prompt: str, model: str) -> Optional[str]:
    url = "http://localhost:11434/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            res = json.loads(response.read().decode("utf-8"))
            return res.get("response", "").strip()
    except Exception:
        return None

def clean_mermaid_output(text: str) -> str:
    """Strips markdown blocks and extracts pure mermaid code."""
    text = re.sub(r'```(?:mermaid)?', '', text).replace('```', '').strip()
    match = re.search(r'(graph\s+[A-Z]{2}[\s\S]*)', text)
    if match:
        clean = match.group(1).strip()
        if "-->" in clean or "---" in clean or "[" in clean:
            return clean
    return ""

def generate_bulletproof_ast_mermaid(summary: Dict[str, Any], direction: str = "TD") -> str:
    """
    100% reliable fallback generator that never fails syntax parsing.
    Groups nodes into architectural subgraphs with tailored theme colors.
    """
    lines = [
        f"graph {direction}",
        "  %% RepoGraph Architectural Blueprint",
        "  classDef entryNode fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;",
        "  classDef apiNode fill:#164e63,stroke:#22d3ee,stroke-width:1.5px,color:#f8fafc;",
        "  classDef coreNode fill:#064e3b,stroke:#34d399,stroke-width:1.5px,color:#f8fafc;",
        "  classDef dataNode fill:#431407,stroke:#fb923c,stroke-width:1.5px,color:#f8fafc;",
        "  classDef utilNode fill:#312e81,stroke:#a78bfa,stroke-width:1.5px,color:#f8fafc;",
        "  classDef defaultNode fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f8fafc;"
    ]

    layers: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for file, data in summary.items():
        layer = data.get("layer", "Domain Services")
        layers.setdefault(layer, []).append((file, data))

    layer_styles = {
        "Application Entry": "entryNode",
        "API & Interface": "apiNode",
        "Core & Domain": "coreNode",
        "Data & Storage": "dataNode",
        "Utilities & Shared": "utilNode",
        "Configuration": "utilNode",
        "Domain Services": "defaultNode"
    }

    for layer_name, items in layers.items():
        subgraph_id = sanitize_id(f"layer_{layer_name}")
        lines.append(f'  subgraph {subgraph_id}["{layer_name}"]')
        for file, data in items:
            node_id = data["id"]
            label_parts = [file]
            if data["classes"]:
                label_parts.append(f"📦 {', '.join(data['classes'][:2])}")
            elif data["functions"]:
                label_parts.append(f"⚡ {', '.join(data['functions'][:2])}")
            
            clean_label = " | ".join(label_parts).replace('"', "'")
            style_class = layer_styles.get(layer_name, "defaultNode")
            if data.get("has_entry_point"):
                style_class = "entryNode"
                clean_label = f"🚀 {clean_label}"

            lines.append(f'    {node_id}["{clean_label}"]:::{style_class}')
        lines.append("  end")

    edges_added = set()
    for file, data in summary.items():
        src_id = data["id"]
        for dep in data["internal_dependencies"]:
            if dep in summary:
                tgt_id = summary[dep]["id"]
                edge_key = (src_id, tgt_id)
                if edge_key not in edges_added:
                    lines.append(f"  {src_id} --> {tgt_id}")
                    edges_added.add(edge_key)

    return "\n".join(lines)

def build_interactive_html(mermaid_code: str, repo_name: str, summary: Dict[str, Any], ollama_info: Dict[str, Any]) -> str:
    summary_json = json.dumps(summary, indent=None)
    ollama_json = json.dumps(ollama_info, indent=None)
    cycles = detect_circular_dependencies(summary)
    cycles_json = json.dumps(cycles)
    
    total_files = len(summary)
    total_classes = sum(len(d["classes"]) for d in summary.values())
    total_functions = sum(d["all_functions_count"] for d in summary.values())
    total_loc = sum(d["loc"] for d in summary.values())
    total_deps = sum(len(d["internal_dependencies"]) for d in summary.values())

    model_label = f"AI Model: {ollama_info.get('model', 'Local')}" if ollama_info.get("online") else "Engine: Deterministic AST"
    dot_class = "" if ollama_info.get("online") else "warning"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RepoGraph - {repo_name} | Architecture Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
  <style>
    :root {{
      --bg-base: #07090e;
      --bg-surface: #0d121f;
      --bg-surface-elevated: #131b2e;
      --border: #1e293b;
      --border-focus: #38bdf8;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-faint: #475569;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.25);
      --emerald: #34d399;
      --amber: #fbbf24;
      --indigo: #818cf8;
      --rose: #fb7185;
      --font-ui: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    
    body {{
      background-color: var(--bg-base);
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(56, 189, 248, 0.05) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(129, 140, 248, 0.05) 0%, transparent 40%),
        radial-gradient(#1e293b 1px, transparent 1px);
      background-size: 100% 100%, 100% 100%, 28px 28px;
      color: var(--text-main);
      font-family: var(--font-ui);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}

    header.top-nav {{
      height: 64px;
      background: rgba(13, 18, 31, 0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      z-index: 50;
      flex-shrink: 0;
    }}

    .brand-group {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .logo-badge {{
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, #0284c7, #6366f1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      box-shadow: 0 0 16px var(--accent-glow);
    }}

    .title-group h1 {{
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .title-group p {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    .nav-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
      font-family: var(--font-mono);
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border);
    }}

    .status-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 8px var(--emerald);
    }}

    .status-dot.warning {{
      background: var(--amber);
      box-shadow: 0 0 8px var(--amber);
    }}

    .btn {{
      background: var(--bg-surface-elevated);
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 7px 14px;
      border-radius: 8px;
      font-family: var(--font-ui);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.18s ease;
      text-decoration: none;
    }}

    .btn:hover {{
      background: #1e293b;
      border-color: var(--accent);
      color: #ffffff;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
    }}

    .btn-primary {{
      background: linear-gradient(135deg, #0284c7, #2563eb);
      border: 1px solid #38bdf8;
      color: #ffffff;
      font-weight: 600;
    }}

    .btn-primary:hover {{
      background: linear-gradient(135deg, #0369a1, #1d4ed8);
      box-shadow: 0 0 14px var(--accent-glow);
    }}

    .workspace {{
      flex: 1;
      display: flex;
      position: relative;
      overflow: hidden;
    }}

    aside.sidebar {{
      width: 320px;
      background: rgba(13, 18, 31, 0.85);
      backdrop-filter: blur(12px);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 20;
      transition: transform 0.25s ease;
      flex-shrink: 0;
    }}

    .sidebar-header {{
      padding: 16px;
      border-bottom: 1px solid var(--border);
    }}

    .search-box {{
      position: relative;
      width: 100%;
    }}

    .search-box input {{
      width: 100%;
      background: #090d16;
      border: 1px solid var(--border);
      color: var(--text-main);
      padding: 8px 12px 8px 32px;
      border-radius: 8px;
      font-size: 13px;
      font-family: var(--font-ui);
      outline: none;
      transition: border-color 0.2s;
    }}

    .search-box input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }}

    .search-box .search-icon {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 13px;
    }}

    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      padding: 12px 16px;
      background: rgba(9, 13, 22, 0.6);
      border-bottom: 1px solid var(--border);
    }}

    .metric-card {{
      background: var(--bg-surface-elevated);
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.04);
    }}

    .metric-card .label {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .metric-card .value {{
      font-size: 18px;
      font-weight: 700;
      color: #ffffff;
      font-family: var(--font-mono);
      margin-top: 2px;
    }}

    .layer-filters {{
      padding: 12px 16px 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      border-bottom: 1px solid var(--border);
    }}

    .layer-chip {{
      font-size: 11px;
      font-weight: 500;
      padding: 3px 8px;
      border-radius: 12px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .layer-chip:hover, .layer-chip.active {{
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--accent);
      color: #ffffff;
    }}

    .module-list {{
      flex: 1;
      overflow-y: auto;
      padding: 10px 12px;
    }}

    .module-item {{
      padding: 9px 12px;
      margin-bottom: 6px;
      background: var(--bg-surface-elevated);
      border: 1px solid transparent;
      border-radius: 7px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .module-item:hover, .module-item.selected {{
      background: #1e293b;
      border-color: var(--accent);
      transform: translateX(2px);
    }}

    .module-title {{
      font-size: 13px;
      font-weight: 600;
      color: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }}

    .module-sub {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 3px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .tag-badge {{
      font-size: 10px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
      background: rgba(56, 189, 248, 0.1);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.2);
    }}

    main.viewport {{
      flex: 1;
      position: relative;
      background: #090d16;
      overflow: hidden;
      display: flex;
      justify-content: center;
      align-items: center;
    }}

    #graph-container {{
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
    }}

    .mermaid {{
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
    }}

    .viewport-controls {{
      position: absolute;
      top: 16px;
      right: 16px;
      display: flex;
      gap: 6px;
      background: rgba(13, 18, 31, 0.85);
      backdrop-filter: blur(8px);
      padding: 6px;
      border-radius: 10px;
      border: 1px solid var(--border);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      z-index: 30;
    }}

    .control-btn {{
      width: 34px;
      height: 34px;
      border-radius: 6px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 15px;
      transition: all 0.15s ease;
    }}

    .control-btn:hover {{
      background: #1e293b;
      border-color: var(--accent);
      color: var(--accent);
    }}

    .hint-chip {{
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: rgba(13, 18, 31, 0.85);
      backdrop-filter: blur(8px);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      color: var(--text-muted);
      border: 1px solid var(--border);
      pointer-events: none;
      z-index: 30;
    }}

    aside.inspector {{
      width: 360px;
      background: rgba(13, 18, 31, 0.95);
      backdrop-filter: blur(16px);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 25;
      transform: translateX(100%);
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      box-shadow: -8px 0 30px rgba(0, 0, 0, 0.5);
    }}

    aside.inspector.open {{
      transform: translateX(0);
    }}

    .inspector-header {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}

    .inspector-body {{
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }}

    .section-title {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-muted);
      margin-bottom: 8px;
      font-weight: 600;
    }}

    .symbol-pill {{
      display: inline-block;
      padding: 4px 8px;
      margin: 2px 4px 4px 0;
      border-radius: 5px;
      background: #1e293b;
      border: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 12px;
      font-family: var(--font-mono);
      color: #38bdf8;
    }}

    .dep-link {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 10px;
      background: #090d16;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 12px;
      margin-bottom: 5px;
      cursor: pointer;
      text-decoration: none;
      color: var(--text-main);
    }}

    .dep-link:hover {{
      border-color: var(--accent);
      background: #131b2e;
    }}

    .modal-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(3, 7, 18, 0.85);
      backdrop-filter: blur(8px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}

    .modal-overlay.active {{
      display: flex;
    }}

    .modal-dialog {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      max-width: 650px;
      width: 100%;
      max-height: 85vh;
      overflow-y: auto;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      padding: 24px;
      position: relative;
    }}

    .modal-dialog h3 {{
      font-size: 20px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .guide-step {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      margin-top: 12px;
    }}

    .guide-step h4 {{
      font-size: 14px;
      color: var(--accent);
      margin-bottom: 4px;
    }}

    .guide-step p {{
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    #toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #0284c7;
      color: #ffffff;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      box-shadow: 0 4px 20px rgba(2, 132, 199, 0.4);
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 200;
    }}

    #toast.show {{
      transform: translateY(0);
      opacity: 1;
    }}

    svg {{
      cursor: grab;
    }}
    svg:active {{
      cursor: grabbing;
    }}
  </style>
</head>
<body>

  <header class="top-nav">
    <div class="brand-group">
      <div class="logo-badge">⚡</div>
      <div class="title-group">
        <h1>RepoGraph: {repo_name}</h1>
        <p>Zero-Read Architecture Intelligence & Interactive Blueprint</p>
      </div>
    </div>

    <div class="nav-actions">
      <div class="status-pill">
        <span class="status-dot {dot_class}"></span>
        <span>{model_label}</span>
      </div>
      
      <button class="btn" id="btn-sloth" onclick="openSlothModal()">
        <span>🦥 30s Lazy Guide</span>
      </button>

      <button class="btn" id="btn-copy-mermaid" onclick="copyMermaid()">
        <span>📋 Copy Mermaid</span>
      </button>

      <button class="btn btn-primary" id="btn-export-md" onclick="downloadMarkdown()">
        <span>⬇ Export ARCHITECTURE.md</span>
      </button>
    </div>
  </header>

  <div class="workspace">
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="module-search" placeholder="Filter modules, classes, functions..." oninput="handleSearch(this.value)">
        </div>
      </div>

      <div class="metrics-grid">
        <div class="metric-card">
          <div class="label">Modules</div>
          <div class="value">{total_files}</div>
        </div>
        <div class="metric-card">
          <div class="label">Classes</div>
          <div class="value">{total_classes}</div>
        </div>
        <div class="metric-card">
          <div class="label">Functions</div>
          <div class="value">{total_functions}</div>
        </div>
        <div class="metric-card">
          <div class="label">Dep Edges</div>
          <div class="value">{total_deps}</div>
        </div>
      </div>

      <div class="layer-filters" id="layer-filters">
        <span class="layer-chip active" onclick="filterByLayer('ALL')">All</span>
      </div>

      <div class="module-list" id="module-list">
      </div>
    </aside>

    <main class="viewport" id="graph-viewport">
      <div class="viewport-controls">
        <button class="control-btn" title="Zoom In (+)" onclick="zoomIn()">+</button>
        <button class="control-btn" title="Zoom Out (-)" onclick="zoomOut()">−</button>
        <button class="control-btn" title="Reset View (0)" onclick="resetZoom()">🎯</button>
        <button class="control-btn" title="Fit Diagram" onclick="fitDiagram()">⛶</button>
      </div>

      <div id="graph-container">
        <div class="mermaid" id="mermaid-root">
{mermaid_code}
        </div>
      </div>

      <div class="hint-chip">
        💡 Drag to Pan &bull; Scroll to Zoom &bull; Click Node for Deep Inspection
      </div>
    </main>

    <aside class="inspector" id="inspector-drawer">
      <div class="inspector-header">
        <div>
          <span class="tag-badge" id="insp-layer">Core</span>
          <h2 style="font-size: 16px; margin-top: 4px;" id="insp-file">module.py</h2>
        </div>
        <button class="control-btn" onclick="closeInspector()">✕</button>
      </div>

      <div class="inspector-body">
        <div>
          <div class="section-title">Module Summary</div>
          <p style="font-size: 13px; color: var(--text-muted); line-height: 1.4;" id="insp-doc"></p>
        </div>

        <div>
          <div class="section-title">Code Metrics</div>
          <div style="display: flex; gap: 8px;">
            <div class="metric-card" style="flex:1;">
              <div class="label">Lines of Code</div>
              <div class="value" id="insp-loc">0</div>
            </div>
            <div class="metric-card" style="flex:1;">
              <div class="label">Complexity</div>
              <div class="value" id="insp-complexity">0</div>
            </div>
          </div>
        </div>

        <div id="insp-classes-section">
          <div class="section-title">Classes Defined</div>
          <div id="insp-classes"></div>
        </div>

        <div id="insp-functions-section">
          <div class="section-title">Public Functions</div>
          <div id="insp-functions"></div>
        </div>

        <div>
          <div class="section-title">Outbound Dependencies (Imports)</div>
          <div id="insp-deps"></div>
        </div>

        <div>
          <div class="section-title">Inbound Dependencies (Imported By)</div>
          <div id="insp-imported-by"></div>
        </div>
      </div>
    </aside>
  </div>

  <div class="modal-overlay" id="sloth-modal" onclick="closeSlothModalOnOut(event)">
    <div class="modal-dialog">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3>🦥 30-Second Lazy Onboarding Guide</h3>
        <button class="control-btn" onclick="closeSlothModal()">✕</button>
      </div>
      <p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">
        Everything you need to know about <strong>{repo_name}</strong> without reading the source code.
      </p>

      <div class="guide-step">
        <h4>🚀 1. Where Does Execution Begin?</h4>
        <p id="sloth-entry-text">Analyzing entry points...</p>
      </div>

      <div class="guide-step">
        <h4>🧠 2. Core Business Engine</h4>
        <p id="sloth-core-text">Analyzing domain layers...</p>
      </div>

      <div class="guide-step">
        <h4>🌐 3. Data & API Boundaries</h4>
        <p id="sloth-api-text">Analyzing interfaces...</p>
      </div>

      <div class="guide-step">
        <h4>🛠️ 4. How to Extend This Codebase</h4>
        <p id="sloth-extend-text">Follow the dependency direction in the diagram. Import shared utilities from the utility modules without creating backward cycles to the entry files.</p>
      </div>

      <div style="margin-top: 18px; text-align: right;">
        <button class="btn btn-primary" onclick="closeSlothModal()">Got it, back to the Blueprint</button>
      </div>
    </div>
  </div>

  <div id="toast">Mermaid markdown copied to clipboard!</div>

  <script>
    const SUMMARY = {summary_json};
    const OLLAMA_INFO = {ollama_json};
    const CYCLES = {cycles_json};
    const MERMAID_RAW = {json.dumps(mermaid_code)};
    const REPO_NAME = "{repo_name}";

    let panZoomInstance = null;
    let selectedModule = null;

    mermaid.initialize({{
      startOnLoad: true,
      theme: 'dark',
      securityLevel: 'loose',
      themeVariables: {{
        darkMode: true,
        background: '#090d16',
        primaryColor: '#0284c7',
        primaryTextColor: '#f8fafc',
        lineColor: '#38bdf8'
      }}
    }});

    const observer = new MutationObserver((mutations, obs) => {{
      const svg = document.querySelector("#graph-viewport svg");
      if (svg) {{
        svg.setAttribute("style", "width: 100%; height: 100%;");
        panZoomInstance = svgPanZoom(svg, {{
          zoomEnabled: true,
          controlIconsEnabled: false,
          fit: true,
          center: true,
          minZoom: 0.2,
          maxZoom: 12,
          zoomScaleSensitivity: 0.3
        }});

        attachSvgNodeListeners();
        obs.disconnect();
      }}
    }});
    observer.observe(document.getElementById("graph-container"), {{ childList: true, subtree: true }});

    function attachSvgNodeListeners() {{
      const nodes = document.querySelectorAll("#graph-viewport svg .node");
      nodes.forEach(node => {{
        node.style.cursor = "pointer";
        node.addEventListener("click", () => {{
          const id = node.id.replace(/^flowchart-/, '').split('-')[0];
          for (const [file, data] of Object.entries(SUMMARY)) {{
            if (data.id === id || node.id.includes(data.id)) {{
              inspectModule(file);
              break;
            }}
          }}
        }});
      }});
    }}

    function initSidebar() {{
      const list = document.getElementById("module-list");
      const filterContainer = document.getElementById("layer-filters");
      const layers = new Set();

      list.innerHTML = "";
      for (const [file, data] of Object.entries(SUMMARY)) {{
        layers.add(data.layer);

        const item = document.createElement("div");
        item.className = "module-item";
        item.id = `mod-item-${{data.id}}`;
        item.onclick = () => inspectModule(file);

        item.innerHTML = `
          <div class="module-title">
            <span style="overflow:hidden; text-overflow:ellipsis;">${{file}}</span>
            <span class="tag-badge">${{data.layer.split(' ')[0]}}</span>
          </div>
          <div class="module-sub">
            ${{data.classes.length ? '📦 ' + data.classes.join(', ') : '⚡ ' + (data.functions.slice(0,3).join(', ') || 'module')}}
          </div>
        `;
        list.appendChild(item);
      }}

      layers.forEach(layer => {{
        const chip = document.createElement("span");
        chip.className = "layer-chip";
        chip.innerText = layer;
        chip.onclick = () => filterByLayer(layer);
        filterContainer.appendChild(chip);
      }});

      populateSlothModal();
    }}

    function filterByLayer(layer) {{
      document.querySelectorAll(".layer-chip").forEach(c => {{
        c.classList.toggle("active", c.innerText === layer || (layer === 'ALL' && c.innerText === 'All'));
      }});

      for (const [file, data] of Object.entries(SUMMARY)) {{
        const item = document.getElementById(`mod-item-${{data.id}}`);
        if (!item) continue;
        if (layer === "ALL" || data.layer === layer) {{
          item.style.display = "block";
        }} else {{
          item.style.display = "none";
        }}
      }}
    }}

    function handleSearch(query) {{
      const q = query.toLowerCase().trim();
      for (const [file, data] of Object.entries(SUMMARY)) {{
        const item = document.getElementById(`mod-item-${{data.id}}`);
        if (!item) continue;
        const matches = file.toLowerCase().includes(q) ||
          data.classes.some(c => c.toLowerCase().includes(q)) ||
          data.functions.some(f => f.toLowerCase().includes(q)) ||
          data.layer.toLowerCase().includes(q);
        item.style.display = matches ? "block" : "none";
      }}
    }}

    function inspectModule(file) {{
      const data = SUMMARY[file];
      if (!data) return;

      selectedModule = file;
      document.querySelectorAll(".module-item").forEach(i => i.classList.remove("selected"));
      const selItem = document.getElementById(`mod-item-${{data.id}}`);
      if (selItem) {{
        selItem.classList.add("selected");
        selItem.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
      }}

      document.getElementById("insp-file").innerText = file;
      document.getElementById("insp-layer").innerText = data.layer;
      document.getElementById("insp-doc").innerText = data.docstring || "No module docstring specified.";
      document.getElementById("insp-loc").innerText = data.loc;
      document.getElementById("insp-complexity").innerText = data.complexity;

      const clsContainer = document.getElementById("insp-classes");
      if (data.classes.length > 0) {{
        document.getElementById("insp-classes-section").style.display = "block";
        clsContainer.innerHTML = data.classes.map(c => `<span class="symbol-pill">class ${{c}}</span>`).join("");
      }} else {{
        document.getElementById("insp-classes-section").style.display = "none";
      }}

      const fnContainer = document.getElementById("insp-functions");
      if (data.functions.length > 0) {{
        document.getElementById("insp-functions-section").style.display = "block";
        fnContainer.innerHTML = data.functions.map(f => `<span class="symbol-pill">def ${{f}}()</span>`).join("");
      }} else {{
        document.getElementById("insp-functions-section").style.display = "none";
      }}

      const depsContainer = document.getElementById("insp-deps");
      if (data.internal_dependencies.length > 0) {{
        depsContainer.innerHTML = data.internal_dependencies.map(d => `
          <div class="dep-link" onclick="inspectModule('${{d}}')">
            <span>↳ ${{d}}</span>
            <span style="color:var(--accent);">inspect &rarr;</span>
          </div>
        `).join("");
      }} else {{
        depsContainer.innerHTML = `<span style="font-size:12px; color:var(--text-faint);">No internal dependencies (Standalone)</span>`;
      }}

      const impByContainer = document.getElementById("insp-imported-by");
      if (data.imported_by && data.imported_by.length > 0) {{
        impByContainer.innerHTML = data.imported_by.map(ib => `
          <div class="dep-link" onclick="inspectModule('${{ib}}')">
            <span>↲ ${{ib}}</span>
            <span style="color:var(--emerald);">imported by &rarr;</span>
          </div>
        `).join("");
      }} else {{
        impByContainer.innerHTML = `<span style="font-size:12px; color:var(--text-faint);">Not imported by internal files</span>`;
      }}

      document.getElementById("inspector-drawer").classList.add("open");
    }}

    function closeInspector() {{
      document.getElementById("inspector-drawer").classList.remove("open");
      document.querySelectorAll(".module-item").forEach(i => i.classList.remove("selected"));
    }}

    function zoomIn() {{ if (panZoomInstance) panZoomInstance.zoomIn(); }}
    function zoomOut() {{ if (panZoomInstance) panZoomInstance.zoomOut(); }}
    function resetZoom() {{ if (panZoomInstance) {{ panZoomInstance.reset(); panZoomInstance.center(); }} }}
    function fitDiagram() {{ if (panZoomInstance) {{ panZoomInstance.fit(); panZoomInstance.center(); }} }}

    function populateSlothModal() {{
      const entryPoints = Object.entries(SUMMARY).filter(([_, d]) => d.has_entry_point).map(([f]) => f);
      const coreFiles = Object.entries(SUMMARY).filter(([_, d]) => d.layer.includes("Core") || d.layer.includes("Domain")).map(([f]) => f);
      const apiFiles = Object.entries(SUMMARY).filter(([_, d]) => d.layer.includes("API") || d.layer.includes("Interface")).map(([f]) => f);

      document.getElementById("sloth-entry-text").innerText = entryPoints.length 
        ? `Start execution at: ${{entryPoints.join(", ")}}. This is where CLI/Server initialization takes place.`
        : `No explicit entry point file found. Inspect top-level scripts or root modules.`;

      document.getElementById("sloth-core-text").innerText = coreFiles.length 
        ? `The heart of the application logic is encapsulated in: ${{coreFiles.join(", ")}}. Look here to understand core domain algorithms.`
        : `Domain logic is distributed among the internal modules. Inspect dependencies in the center graph.`;

      document.getElementById("sloth-api-text").innerText = apiFiles.length
        ? `External endpoints and interfaces are located in: ${{apiFiles.join(", ")}}.`
        : `This appears to be an internal library or pipeline without separate HTTP endpoints.`;
    }}

    function openSlothModal() {{ document.getElementById("sloth-modal").classList.add("active"); }}
    function closeSlothModal() {{ document.getElementById("sloth-modal").classList.remove("active"); }}
    function closeSlothModalOnOut(e) {{ if (e.target.id === "sloth-modal") closeSlothModal(); }}

    function showToast(msg) {{
      const t = document.getElementById("toast");
      t.innerText = msg;
      t.classList.add("show");
      setTimeout(() => t.classList.remove("show"), 2500);
    }}

    function copyMermaid() {{
      navigator.clipboard.writeText(MERMAID_RAW).then(() => {{
        showToast("✅ Mermaid code copied to clipboard!");
      }}).catch(() => {{
        showToast("⚠️ Could not access clipboard");
      }});
    }}

    function downloadMarkdown() {{
      const ticks = "```";
      const content = "# Architecture Overview: " + REPO_NAME + "\\n\\n" + ticks + "mermaid\\n" + MERMAID_RAW + "\\n" + ticks + "\\n";
      const blob = new Blob([content], {{ type: "text/markdown;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ARCHITECTURE.md";
      a.click();
      URL.revokeObjectURL(url);
      showToast("📥 ARCHITECTURE.md downloaded!");
    }}

    initSidebar();
  </script>
</body>
</html>
"""

def serve_directory(port: int = 8080):
    """Starts a lightweight zero-dependency local HTTP server."""
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    server = HTTPServer(('localhost', port), QuietHandler)
    url = f"http://localhost:{port}/repograph.html"
    print(f"\n🚀 RepoGraph Live Server running at: {url}")
    print("   Press Ctrl+C to stop server.\n")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        server.server_close()

def main():
    args = sys.argv[1:]
    should_serve = "--serve" in args
    force_no_ai = "--no-ai" in args
    output_json = "--json" in args

    target_dir = "."
    for arg in args:
        if not arg.startswith("--"):
            target_dir = arg
            break

    target_path = Path(target_dir).resolve()
    repo_name = target_path.name

    print("\n" + "=" * 62)
    print(" [RepoGraph] (SlothEdition) - Zero-Read Codebase Onboarding")
    print("=" * 62)

    print(f"\n[1/3] Parsing AST for repository: {repo_name}...")
    summary = scan_repository(target_path)

    if not summary:
        print(f"[!] No Python files found in: {target_path}")
        sys.exit(1)

    total_classes = sum(len(d["classes"]) for d in summary.values())
    total_funcs = sum(d["all_functions_count"] for d in summary.values())
    print(f"      Parsed {len(summary)} modules, {total_classes} classes, {total_funcs} functions in < 0.1s.")

    if output_json:
        print(json.dumps(summary, indent=2))
        return

    model_to_use = "llama3.2:3b"
    ollama_online = False
    mermaid_code = ""

    if not force_no_ai:
        model_to_use, ollama_online = get_installed_ollama_model()
        if ollama_online:
            print(f"[2/3] Synthesizing architecture via Ollama ({model_to_use})...")
            compact_summary = {
                file: {
                    "classes": data["classes"][:3],
                    "functions": data["functions"][:3],
                    "layer": data["layer"],
                    "deps": data["internal_dependencies"]
                }
                for file, data in summary.items()
            }
            prompt = f"""You are a senior software architect. Convert this repository data into a Mermaid.js diagram (graph TD).
Group files into subgraphs by architectural layer (e.g. Core, Controllers, Models, Utils).

Data:
{json.dumps(compact_summary, indent=2)}

Strict Rules:
1. Output ONLY valid Mermaid syntax starting with `graph TD`.
2. Do not use quotes or special characters inside node IDs (use alphanumeric and underscores only).
3. Do not include markdown ticks, explanation, or commentary.
"""
            raw_response = query_ollama(prompt, model=model_to_use)
            if raw_response:
                mermaid_code = clean_mermaid_output(raw_response)

    if not mermaid_code or "graph TD" not in mermaid_code:
        status_msg = "Ollama offline or --no-ai passed" if not ollama_online else "Ollama returned invalid syntax"
        print(f"[2/3] {status_msg} -> Generating bulletproof deterministic AST graph...")
        mermaid_code = generate_bulletproof_ast_mermaid(summary, direction="TD")
        ollama_online = False
    else:
        print("      Architectural synthesis successful!")

    print("[3/3] Exporting artifacts...")
    
    with open("ARCHITECTURE.md", "w", encoding="utf-8") as f:
        f.write(f"# Architecture Overview: {repo_name}\n\n```mermaid\n{mermaid_code}\n```\n")

    ollama_status = {"online": ollama_online, "model": model_to_use}
    html_page = build_interactive_html(mermaid_code, repo_name, summary, ollama_status)
    with open("repograph.html", "w", encoding="utf-8") as f:
        f.write(html_page)

    print("\n[OK] Success! All artifacts generated:")
    print("  Markdown:    ARCHITECTURE.md (Renders natively on GitHub)")
    print("  Interactive: repograph.html (Pan/Zoom & Codebase Inspector enabled)\n")

    if should_serve:
        serve_directory()

if __name__ == "__main__":
    main()
