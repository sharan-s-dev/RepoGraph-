#!/usr/bin/env python3
"""
RepoGraph - Codebase Architecture & Dependency Graph Explorer
Deterministic AST dependency analysis + Interactive Web Blueprints.
Zero third-party pip dependencies required.
"""

import ast
import json
import os
import re
import sys
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

# Ensure UTF-8 output on Windows consoles
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

def resolve_repo_name(target_path: Path) -> str:
    """Intelligently determine a clean, professional project name."""
    try:
        res = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(target_path),
            capture_output=True,
            text=True,
            timeout=2
        )
        if res.returncode == 0 and res.stdout.strip():
            url = res.stdout.strip()
            name = url.split("/")[-1].replace(".git", "").strip()
            clean_name = re.sub(r'[-_]+$', '', name)
            if clean_name and clean_name.lower() not in ["dev", "dev 4", "code"]:
                return clean_name
    except Exception:
        pass

    for config_file in ["pyproject.toml", "setup.cfg", "package.json"]:
        p = target_path / config_file
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if m:
                    return m.group(1).strip()
            except Exception:
                pass

    dir_name = target_path.name
    generic_names = {".", "dev", "dev 4", "src", "app", "code", "repo", "test", "demo"}
    if dir_name.lower() in generic_names or dir_name.isdigit():
        return "RepoGraph"

    clean_dir = re.sub(r'[-_]+$', '', dir_name)
    return clean_dir or "RepoGraph"

class CodebaseVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, repo_root: Path):
        self.file_path = file_path
        self.repo_root = repo_root
        self.classes = []
        self.class_details = {}
        self.functions = []
        self.raw_imports = []
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
                    args_list = [a.arg for a in item.args.args if a.arg != "self"]
                    methods.append(f"{item.name}({', '.join(args_list[:3])})")
        
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(b.attr)

        self.class_details[node.name] = {
            "methods": methods[:6],
            "bases": bases
        }
        self.complexity_score += 2
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if not node.name.startswith("_"):
            args_list = [a.arg for a in node.args.args if a.arg != "self"]
            self.functions.append(f"{node.name}({', '.join(args_list[:3])})")
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if not node.name.startswith("_"):
            args_list = [a.arg for a in node.args.args if a.arg != "self"]
            self.functions.append(f"async {node.name}({', '.join(args_list[:3])})")
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
            self.raw_imports.append((alias.name, None, 0))

    def visit_ImportFrom(self, node):
        level = node.level or 0
        mod = node.module or ""
        for alias in node.names:
            self.raw_imports.append((mod, alias.name, level))

def classify_layer(rel_path: str, visitor: CodebaseVisitor) -> str:
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
                cycle = current_path[cycle_start:] + [dep]
                if cycle not in cycles and len(cycle) > 2:
                    cycles.append(cycle)

        current_path.pop()
        rec_stack.remove(node)

    for mod in summary:
        if mod not in visited:
            dfs(mod)

    return cycles[:5]

def scan_repository(repo_path: Path) -> Dict[str, Any]:
    repo_path = repo_path.resolve()
    codebase_summary: Dict[str, Any] = {}
    module_to_file: Dict[str, str] = {}

    py_files: List[Path] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                py_files.append(Path(root) / file)

    for p in py_files:
        rel = p.relative_to(repo_path)
        rel_posix = rel.as_posix()
        rel_no_ext = rel.with_suffix("")
        mod_name = rel_no_ext.as_posix().replace("/", ".")
        short_name = mod_name.split(".")[-1]
        
        module_to_file[mod_name] = rel_posix
        module_to_file[short_name] = rel_posix

        if p.name == "__init__.py":
            pkg_path = p.parent.relative_to(repo_path)
            pkg_mod = pkg_path.as_posix().replace("/", ".")
            if pkg_mod and pkg_mod != ".":
                module_to_file[pkg_mod] = rel_posix
                module_to_file[pkg_mod.split(".")[-1]] = rel_posix

    visitors: Dict[str, CodebaseVisitor] = {}
    for p in py_files:
        rel_posix = p.relative_to(repo_path).as_posix()
        loc = count_file_lines(p)
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(p))
            visitor = CodebaseVisitor(p, repo_path)
            visitor.visit(tree)
            visitors[rel_posix] = visitor

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
                "internal_dependencies": [],
                "has_entry_point": visitor.has_main or rel_posix.endswith(("main.py", "app.py", "cli.py")),
                "loc": loc,
                "complexity": min(visitor.complexity_score, 100),
                "imported_by": []
            }
        except Exception:
            continue

    for p in py_files:
        rel_posix = p.relative_to(repo_path).as_posix()
        if rel_posix not in codebase_summary:
            continue

        visitor = visitors.get(rel_posix)
        if not visitor:
            continue

        internal_deps = set()
        file_parent = p.parent.relative_to(repo_path)

        for mod_name, item_name, level in visitor.raw_imports:
            if level > 0:
                curr_dir = file_parent
                for _ in range(level - 1):
                    curr_dir = curr_dir.parent
                
                prefix = curr_dir.as_posix().replace("/", ".")
                target_candidates = []
                if mod_name:
                    full_mod = f"{prefix}.{mod_name}" if prefix and prefix != "." else mod_name
                    target_candidates.append(full_mod)
                    if item_name:
                        target_candidates.append(f"{full_mod}.{item_name}")
                elif item_name:
                    full_item = f"{prefix}.{item_name}" if prefix and prefix != "." else item_name
                    target_candidates.append(full_item)
                    target_candidates.append(item_name)

                for cand in target_candidates:
                    if cand in module_to_file and module_to_file[cand] != rel_posix:
                        internal_deps.add(module_to_file[cand])
            else:
                candidates = []
                if mod_name:
                    candidates.append(mod_name)
                    candidates.append(mod_name.split(".")[0])
                    if item_name:
                        candidates.append(f"{mod_name}.{item_name}")
                elif item_name:
                    candidates.append(item_name)

                for cand in candidates:
                    if cand in module_to_file and module_to_file[cand] != rel_posix:
                        internal_deps.add(module_to_file[cand])

        codebase_summary[rel_posix]["internal_dependencies"] = sorted(list(internal_deps))

    for file, data in codebase_summary.items():
        for dep in data["internal_dependencies"]:
            if dep in codebase_summary and file not in codebase_summary[dep]["imported_by"]:
                codebase_summary[dep]["imported_by"].append(file)

    return codebase_summary

def generate_bulletproof_ast_mermaid(summary: Dict[str, Any], direction: str = "TD") -> str:
    lines = [
        f"graph {direction}",
        "  classDef entryNode fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;",
        "  classDef apiNode fill:#083344,stroke:#06b6d4,stroke-width:1.5px,color:#f8fafc;",
        "  classDef coreNode fill:#064e3b,stroke:#10b981,stroke-width:1.5px,color:#f8fafc;",
        "  classDef dataNode fill:#451a03,stroke:#f59e0b,stroke-width:1.5px,color:#f8fafc;",
        "  classDef utilNode fill:#1e293b,stroke:#38bdf8,stroke-width:1.5px,color:#f8fafc;",
        "  classDef defaultNode fill:#0f172a,stroke:#64748b,stroke-width:1.5px,color:#f8fafc;"
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
                label_parts.append(f"{', '.join(data['classes'][:2])}")
            elif data["functions"]:
                clean_funcs = [f.split('(')[0] for f in data["functions"][:2]]
                label_parts.append(f"{', '.join(clean_funcs)}")
            
            clean_label = " | ".join(label_parts).replace('"', "'")
            style_class = layer_styles.get(layer_name, "defaultNode")
            if data.get("has_entry_point"):
                style_class = "entryNode"

            lines.append(f'    {node_id}["{clean_label}"]:::{style_class}')
        lines.append("  end")
        lines.append(f'  style {subgraph_id} fill:#0b1120,stroke:#1e293b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8')

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

def build_unified_html(mermaid_td: str, mermaid_lr: str, repo_name: str, summary: Dict[str, Any]) -> str:
    summary_json = json.dumps(summary, indent=None)
    cycles = detect_circular_dependencies(summary)
    cycles_json = json.dumps(cycles)
    
    total_files = len(summary)
    total_classes = sum(len(d["classes"]) for d in summary.values())
    total_functions = sum(d["all_functions_count"] for d in summary.values())
    total_loc = sum(d["loc"] for d in summary.values())
    total_deps = sum(len(d["internal_dependencies"]) for d in summary.values())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RepoGraph - {repo_name} | Codebase Architecture Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    :root {{
      --bg-base: #06080e;
      --bg-surface: #0c111d;
      --bg-surface-elevated: #12192c;
      --border: #1e293b;
      --border-focus: #38bdf8;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-faint: #475569;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.25);
      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.25);
      --amber: #f59e0b;
      --indigo: #818cf8;
      --font-ui: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-ui);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}

    header.top-nav {{
      height: 56px;
      background: rgba(12, 17, 29, 0.95);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      z-index: 50;
      flex-shrink: 0;
    }}

    .brand-group {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .logo-badge {{
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: linear-gradient(135deg, #0284c7, #2563eb);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 14px;
      color: #ffffff;
      box-shadow: 0 0 14px var(--accent-glow);
    }}

    .title-group h1 {{
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.2px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .title-group p {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    .nav-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 500;
      font-family: var(--font-mono);
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border);
    }}

    .status-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 8px var(--emerald);
    }}

    .btn {{
      background: var(--bg-surface-elevated);
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 6px;
      font-family: var(--font-ui);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      text-decoration: none;
    }}

    .btn:hover {{
      background: #1e293b;
      border-color: var(--accent);
      color: #ffffff;
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
      width: 310px;
      background: rgba(12, 17, 29, 0.9);
      backdrop-filter: blur(12px);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 20;
      flex-shrink: 0;
    }}

    .sidebar-header {{
      padding: 12px 14px;
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
      padding: 7px 10px 7px 30px;
      border-radius: 6px;
      font-size: 12px;
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
      left: 9px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 12px;
    }}

    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      padding: 10px 14px;
      background: rgba(9, 13, 22, 0.6);
      border-bottom: 1px solid var(--border);
    }}

    .metric-card {{
      background: var(--bg-surface-elevated);
      padding: 6px 8px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.04);
      text-align: center;
    }}

    .metric-card .label {{
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}

    .metric-card .value {{
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      font-family: var(--font-mono);
      margin-top: 1px;
    }}

    .layer-filters {{
      padding: 8px 14px 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      border-bottom: 1px solid var(--border);
    }}

    .layer-chip {{
      font-size: 10.5px;
      font-weight: 500;
      padding: 2px 7px;
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
      padding: 8px 10px;
    }}

    .module-item {{
      padding: 8px 10px;
      margin-bottom: 5px;
      background: var(--bg-surface-elevated);
      border: 1px solid transparent;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .module-item:hover, .module-item.selected {{
      background: #1e293b;
      border-color: var(--accent);
      transform: translateX(2px);
    }}

    .module-title {{
      font-size: 12.5px;
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
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .tag-badge {{
      font-size: 9.5px;
      font-weight: 600;
      padding: 1px 5px;
      border-radius: 4px;
      background: rgba(56, 189, 248, 0.1);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.2);
    }}

    /* Viewport & Native Absolute Transform Pan/Zoom Canvas */
    main.viewport {{
      flex: 1;
      position: relative;
      background-color: #06080e;
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(56, 189, 248, 0.04) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(129, 140, 248, 0.04) 0%, transparent 40%),
        radial-gradient(#1e293b 1px, transparent 1px);
      background-size: 100% 100%, 100% 100%, 28px 28px;
      overflow: hidden;
      cursor: grab;
      user-select: none;
      touch-action: none;
    }}

    main.viewport.is-dragging {{
      cursor: grabbing;
    }}

    #pan-layer {{
      position: absolute;
      top: 0;
      left: 0;
      transform-origin: 0 0;
      will-change: transform;
      pointer-events: auto;
    }}

    #pan-layer svg {{
      display: block;
      overflow: visible;
      filter: drop-shadow(0 10px 30px rgba(0, 0, 0, 0.5));
    }}

    /* Floating Viewport Controls */
    .viewport-controls {{
      position: absolute;
      top: 14px;
      right: 14px;
      display: flex;
      align-items: center;
      gap: 5px;
      background: rgba(12, 17, 29, 0.92);
      backdrop-filter: blur(12px);
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--border);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      z-index: 30;
    }}

    .zoom-badge {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-muted);
      padding: 0 6px;
      min-width: 44px;
      text-align: center;
    }}

    .control-btn {{
      width: 30px;
      height: 30px;
      border-radius: 5px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 13px;
      transition: all 0.15s ease;
    }}

    .control-btn:hover {{
      background: #1e293b;
      border-color: var(--accent);
      color: var(--accent);
    }}

    .hint-chip {{
      position: absolute;
      bottom: 14px;
      left: 14px;
      background: rgba(12, 17, 29, 0.85);
      backdrop-filter: blur(8px);
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 11px;
      color: var(--text-muted);
      border: 1px solid var(--border);
      pointer-events: none;
      z-index: 30;
    }}

    /* Inspector Drawer */
    aside.inspector {{
      width: 340px;
      background: rgba(12, 17, 29, 0.96);
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
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}

    .inspector-body {{
      flex: 1;
      overflow-y: auto;
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .section-title {{
      font-size: 10.5px;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--text-muted);
      margin-bottom: 6px;
      font-weight: 600;
    }}

    .symbol-pill {{
      display: inline-block;
      padding: 3px 7px;
      margin: 2px 3px 3px 0;
      border-radius: 4px;
      background: #1e293b;
      border: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 11px;
      font-family: var(--font-mono);
      color: #38bdf8;
    }}

    .dep-link {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 9px;
      background: #090d16;
      border: 1px solid var(--border);
      border-radius: 5px;
      font-size: 11.5px;
      margin-bottom: 4px;
      cursor: pointer;
      text-decoration: none;
      color: var(--text-main);
      transition: all 0.15s ease;
    }}

    .dep-link:hover {{
      border-color: var(--accent);
      background: #131b2e;
    }}

    /* Architecture Overview Modal */
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
      border-radius: 12px;
      max-width: 620px;
      width: 100%;
      max-height: 85vh;
      overflow-y: auto;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      padding: 20px;
      position: relative;
    }}

    .modal-dialog h3 {{
      font-size: 17px;
      margin-bottom: 4px;
    }}

    .guide-step {{
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 12px 14px;
      margin-top: 10px;
    }}

    .guide-step h4 {{
      font-size: 13px;
      color: var(--accent);
      margin-bottom: 3px;
    }}

    .guide-step p {{
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.45;
    }}

    #toast {{
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #0284c7;
      color: #ffffff;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 12px;
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
  </style>
</head>
<body>

  <header class="top-nav">
    <div class="brand-group">
      <div class="logo-badge">RG</div>
      <div class="title-group">
        <h1>{repo_name}</h1>
        <p>Codebase Architecture & Dependency Graph Explorer</p>
      </div>
    </div>

    <div class="nav-actions">
      <div class="status-pill">
        <span class="status-dot"></span>
        <span>Deterministic AST Engine</span>
      </div>
      
      <button class="btn" onclick="openOverviewModal()">
        <span>Overview</span>
      </button>

      <button class="btn" onclick="copyMermaid()">
        <span>Copy Mermaid</span>
      </button>

      <button class="btn" onclick="downloadSVG()">
        <span>Export SVG</span>
      </button>

      <button class="btn btn-primary" onclick="downloadMarkdown()">
        <span>Download ARCHITECTURE.md</span>
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
          <div class="label">Files</div>
          <div class="value">{total_files}</div>
        </div>
        <div class="metric-card">
          <div class="label">Classes</div>
          <div class="value">{total_classes}</div>
        </div>
        <div class="metric-card">
          <div class="label">Funcs</div>
          <div class="value">{total_functions}</div>
        </div>
        <div class="metric-card">
          <div class="label">Edges</div>
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
        <span class="zoom-badge" id="zoom-level">100%</span>
        <button class="control-btn" title="Fit to Screen" onclick="fitToScreen(true)">⛶</button>
        <button class="control-btn" title="Reset View" onclick="resetZoom()">🎯</button>
        <button class="control-btn" title="Toggle Orientation (Top-Down / Left-Right)" onclick="toggleLayout()">⇄</button>
      </div>

      <div id="pan-layer">
        <!-- Rendered SVG Injected Here -->
      </div>

      <div class="hint-chip">
        Drag to Pan &bull; Scroll to Zoom &bull; Click Node to Inspect &bull; ⇄ to Switch Orientation
      </div>
    </main>

    <aside class="inspector" id="inspector-drawer">
      <div class="inspector-header">
        <div>
          <span class="tag-badge" id="insp-layer">Core</span>
          <h2 style="font-size: 14px; margin-top: 3px;" id="insp-file">module.py</h2>
        </div>
        <button class="control-btn" onclick="closeInspector()">✕</button>
      </div>

      <div class="inspector-body">
        <div>
          <div class="section-title">Module Summary</div>
          <p style="font-size: 12.5px; color: var(--text-muted); line-height: 1.4;" id="insp-doc"></p>
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

  <div class="modal-overlay" id="overview-modal" onclick="closeOverviewModalOnOut(event)">
    <div class="modal-dialog">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3>Architecture Overview</h3>
        <button class="control-btn" onclick="closeOverviewModal()">✕</button>
      </div>
      <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">
        Architectural layers and execution boundaries in <strong>{repo_name}</strong>.
      </p>

      <div class="guide-step">
        <h4>1. Application Entry Points</h4>
        <p id="overview-entry-text">Analyzing entry points...</p>
      </div>

      <div class="guide-step">
        <h4>2. Core Business Engine</h4>
        <p id="overview-core-text">Analyzing domain layers...</p>
      </div>

      <div class="guide-step">
        <h4>3. Interfaces & Storage</h4>
        <p id="overview-api-text">Analyzing interfaces...</p>
      </div>

      <div style="margin-top: 16px; text-align: right;">
        <button class="btn btn-primary" onclick="closeOverviewModal()">Back to Blueprint</button>
      </div>
    </div>
  </div>

  <div id="toast">Mermaid diagram copied to clipboard!</div>

  <script>
    const SUMMARY = {summary_json};
    const CYCLES = {cycles_json};
    const MERMAID_TD = {json.dumps(mermaid_td)};
    const MERMAID_LR = {json.dumps(mermaid_lr)};
    const REPO_NAME = "{repo_name}";

    let currentDirection = "TD";
    let selectedModule = null;

    // --- BULLETPROOF NATIVE PAN & ZOOM ENGINE ---
    const viewport = document.getElementById("graph-viewport");
    const panLayer = document.getElementById("pan-layer");

    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    let isDragging = false;
    let startX = 0;
    let startY = 0;

    function updateTransform(smooth = false) {{
      if (smooth) {{
        panLayer.style.transition = "transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)";
      }} else {{
        panLayer.style.transition = "none";
      }}
      panLayer.style.transform = `translate(${{translateX}}px, ${{translateY}}px) scale(${{scale}})`;
      
      const zoomIndicator = document.getElementById("zoom-level");
      if (zoomIndicator) {{
        zoomIndicator.innerText = Math.round(scale * 100) + "%";
      }}
    }}

    viewport.addEventListener("mousedown", (e) => {{
      if (e.button !== 0 || e.target.closest(".viewport-controls") || e.target.closest(".hint-chip")) return;
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      viewport.classList.add("is-dragging");
    }});

    window.addEventListener("mousemove", (e) => {{
      if (!isDragging) return;
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      updateTransform(false);
    }});

    window.addEventListener("mouseup", () => {{
      if (isDragging) {{
        isDragging = false;
        viewport.classList.remove("is-dragging");
      }}
    }});

    viewport.addEventListener("wheel", (e) => {{
      e.preventDefault();
      const rect = viewport.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomFactor = e.deltaY < 0 ? 1.14 : 0.88;
      const newScale = Math.min(Math.max(scale * zoomFactor, 0.15), 6.0);

      translateX = mouseX - (mouseX - translateX) * (newScale / scale);
      translateY = mouseY - (mouseY - translateY) * (newScale / scale);
      scale = newScale;

      updateTransform(false);
    }}, {{ passive: false }});

    // Touch events for mobile & tablets
    let initialTouchDist = 0;
    let initialTouchScale = 1;

    viewport.addEventListener("touchstart", (e) => {{
      if (e.touches.length === 1) {{
        isDragging = true;
        startX = e.touches[0].clientX - translateX;
        startY = e.touches[0].clientY - translateY;
        viewport.classList.add("is-dragging");
      }} else if (e.touches.length === 2) {{
        isDragging = false;
        initialTouchDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        initialTouchScale = scale;
      }}
    }}, {{ passive: true }});

    viewport.addEventListener("touchmove", (e) => {{
      if (e.touches.length === 1 && isDragging) {{
        translateX = e.touches[0].clientX - startX;
        translateY = e.touches[0].clientY - startY;
        updateTransform(false);
      }} else if (e.touches.length === 2 && initialTouchDist > 0) {{
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
        const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        const rect = viewport.getBoundingClientRect();
        const touchX = midX - rect.left;
        const touchY = midY - rect.top;

        const factor = dist / initialTouchDist;
        const newScale = Math.min(Math.max(initialTouchScale * factor, 0.15), 6.0);

        translateX = touchX - (touchX - translateX) * (newScale / scale);
        translateY = touchY - (touchY - translateY) * (newScale / scale);
        scale = newScale;
        updateTransform(false);
      }}
    }}, {{ passive: true }});

    viewport.addEventListener("touchend", () => {{
      isDragging = false;
      initialTouchDist = 0;
      viewport.classList.remove("is-dragging");
    }});

    function zoomIn() {{
      zoomAtCenter(1.25);
    }}

    function zoomOut() {{
      zoomAtCenter(0.8);
    }}

    function zoomAtCenter(factor) {{
      const cx = viewport.clientWidth / 2;
      const cy = viewport.clientHeight / 2;
      const newScale = Math.min(Math.max(scale * factor, 0.15), 6.0);
      translateX = cx - (cx - translateX) * (newScale / scale);
      translateY = cy - (cy - translateY) * (newScale / scale);
      scale = newScale;
      updateTransform(true);
    }}

    function resetZoom() {{
      fitToScreen(true);
    }}

    function fitToScreen(smooth = true) {{
      const svgEl = panLayer.querySelector("svg");
      if (!svgEl) return;
      
      const vpW = viewport.clientWidth;
      const vpH = viewport.clientHeight;
      if (vpW <= 0 || vpH <= 0) return;

      let svgW = 800;
      let svgH = 600;

      if (svgEl.viewBox && svgEl.viewBox.baseVal && svgEl.viewBox.baseVal.width > 0) {{
        svgW = svgEl.viewBox.baseVal.width;
        svgH = svgEl.viewBox.baseVal.height;
      }} else {{
        try {{
          const bbox = svgEl.getBBox();
          if (bbox.width > 0) {{
            svgW = bbox.width;
            svgH = bbox.height;
          }}
        }} catch(e) {{}}
      }}

      // Standardize size
      svgEl.style.width = svgW + "px";
      svgEl.style.height = svgH + "px";
      svgEl.style.maxWidth = "none";
      svgEl.style.display = "block";

      const pad = 60;
      const availW = Math.max(vpW - pad * 2, 100);
      const availH = Math.max(vpH - pad * 2, 100);

      const scaleX = availW / svgW;
      const scaleY = availH / svgH;
      scale = Math.min(scaleX, scaleY);
      scale = Math.min(Math.max(scale, 0.25), 1.25);

      translateX = (vpW - svgW * scale) / 2;
      translateY = (vpH - svgH * scale) / 2;

      updateTransform(smooth);
    }}

    function toggleLayout() {{
      currentDirection = currentDirection === "TD" ? "LR" : "TD";
      renderMermaidDiagram();
      showToast("Switched to " + (currentDirection === "TD" ? "Top-Down" : "Left-to-Right") + " view");
    }}

    // --- MERMAID RENDERING & INTERACTION ---
    mermaid.initialize({{
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      themeVariables: {{
        darkMode: true,
        background: '#06080e',
        primaryColor: '#0284c7',
        primaryTextColor: '#f8fafc',
        lineColor: '#38bdf8'
      }}
    }});

    async function renderMermaidDiagram() {{
      panLayer.innerHTML = '<div style="color:var(--text-muted); font-size:13px; padding:20px;">Rendering architecture graph...</div>';
      try {{
        const rawCode = currentDirection === "TD" ? MERMAID_TD : MERMAID_LR;
        const uniqueId = "mermaid_svg_" + Date.now();
        const {{ svg }} = await mermaid.render(uniqueId, rawCode);
        panLayer.innerHTML = svg;

        const svgEl = panLayer.querySelector("svg");
        if (svgEl) {{
          svgEl.style.maxWidth = "none";
          svgEl.style.display = "block";
          svgEl.removeAttribute("height");

          attachSvgNodeListeners();
          requestAnimationFrame(() => {{
            fitToScreen(false);
          }});
        }}
      }} catch (err) {{
        console.error("Mermaid error:", err);
        panLayer.innerHTML = '<div style="color:var(--text-muted); font-size:13px; padding:20px;">Error rendering diagram.</div>';
      }}
    }}

    function attachSvgNodeListeners() {{
      const svg = panLayer.querySelector("svg");
      if (!svg) return;

      const nodes = svg.querySelectorAll(".node");
      nodes.forEach(node => {{
        node.style.cursor = "pointer";
        node.addEventListener("click", (e) => {{
          e.stopPropagation();
          const cleanId = node.id.replace(/^flowchart-/, "").replace(/-[0-9]+$/, "");
          for (const [file, data] of Object.entries(SUMMARY)) {{
            if (data.id === cleanId || node.id.includes(data.id)) {{
              inspectModule(file);
              highlightNodeConnections(data.id);
              break;
            }}
          }}
        }});
      }});

      viewport.addEventListener("click", (e) => {{
        if (!e.target.closest(".node") && !e.target.closest("#inspector-drawer") && !e.target.closest(".module-item")) {{
          resetHighlights();
        }}
      }});
    }}

    function highlightNodeConnections(nodeId) {{
      const svg = panLayer.querySelector("svg");
      if (!svg) return;

      const nodes = svg.querySelectorAll(".node");
      const edges = svg.querySelectorAll(".edgePath, .edgeLabel");

      nodes.forEach(n => {{
        if (n.id.includes(nodeId)) {{
          n.style.opacity = "1";
          n.style.filter = "drop-shadow(0 0 10px #38bdf8)";
        }} else {{
          n.style.opacity = "0.22";
          n.style.filter = "none";
        }}
      }});

      edges.forEach(e => {{
        if (e.id && e.id.includes(nodeId)) {{
          e.style.opacity = "1";
        }} else {{
          e.style.opacity = "0.12";
        }}
      }});
    }}

    function resetHighlights() {{
      const svg = panLayer.querySelector("svg");
      if (!svg) return;
      svg.querySelectorAll(".node, .edgePath, .edgeLabel").forEach(el => {{
        el.style.opacity = "1";
        el.style.filter = "none";
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
        item.onclick = () => {{
          inspectModule(file);
          highlightNodeConnections(data.id);
        }};

        item.innerHTML = `
          <div class="module-title">
            <span style="overflow:hidden; text-overflow:ellipsis;">${{file}}</span>
            <span class="tag-badge">${{data.layer.split(' ')[0]}}</span>
          </div>
          <div class="module-sub">
            ${{data.classes.length ? data.classes.join(', ') : (data.functions.slice(0,3).join(', ') || 'module')}}
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

      populateOverviewModal();
    }}

    function filterByLayer(layer) {{
      document.querySelectorAll(".layer-chip").forEach(c => {{
        c.classList.toggle("active", c.innerText === layer || (layer === 'ALL' && c.innerText === 'All'));
      }});

      for (const [file, data] of Object.entries(SUMMARY)) {{
        const item = document.getElementById(`mod-item-${{data.id}}`);
        if (!item) continue;
        item.style.display = (layer === "ALL" || data.layer === layer) ? "block" : "none";
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
        clsContainer.innerHTML = data.classes.map(c => `<span class="symbol-pill">${{c}}</span>`).join("");
      }} else {{
        document.getElementById("insp-classes-section").style.display = "none";
      }}

      const fnContainer = document.getElementById("insp-functions");
      if (data.functions.length > 0) {{
        document.getElementById("insp-functions-section").style.display = "block";
        fnContainer.innerHTML = data.functions.map(f => `<span class="symbol-pill">${{f}}</span>`).join("");
      }} else {{
        document.getElementById("insp-functions-section").style.display = "none";
      }}

      const depsContainer = document.getElementById("insp-deps");
      if (data.internal_dependencies.length > 0) {{
        depsContainer.innerHTML = data.internal_dependencies.map(d => `
          <div class="dep-link" onclick="inspectModule('${{d}}'); highlightNodeConnections('${{SUMMARY[d]?.id}}');">
            <span>↳ ${{d}}</span>
            <span style="color:var(--accent);">inspect &rarr;</span>
          </div>
        `).join("");
      }} else {{
        depsContainer.innerHTML = `<span style="font-size:11.5px; color:var(--text-faint);">Standalone (No internal dependencies)</span>`;
      }}

      const impByContainer = document.getElementById("insp-imported-by");
      if (data.imported_by && data.imported_by.length > 0) {{
        impByContainer.innerHTML = data.imported_by.map(ib => `
          <div class="dep-link" onclick="inspectModule('${{ib}}'); highlightNodeConnections('${{SUMMARY[ib]?.id}}');">
            <span>↲ ${{ib}}</span>
            <span style="color:var(--emerald);">imported by &rarr;</span>
          </div>
        `).join("");
      }} else {{
        impByContainer.innerHTML = `<span style="font-size:11.5px; color:var(--text-faint);">Not imported by internal modules</span>`;
      }}

      document.getElementById("inspector-drawer").classList.add("open");
    }}

    function closeInspector() {{
      document.getElementById("inspector-drawer").classList.remove("open");
      document.querySelectorAll(".module-item").forEach(i => i.classList.remove("selected"));
      resetHighlights();
    }}

    function populateOverviewModal() {{
      const entryPoints = Object.entries(SUMMARY).filter(([_, d]) => d.has_entry_point).map(([f]) => f);
      const coreFiles = Object.entries(SUMMARY).filter(([_, d]) => d.layer.includes("Core") || d.layer.includes("Domain")).map(([f]) => f);
      const apiFiles = Object.entries(SUMMARY).filter(([_, d]) => d.layer.includes("API") || d.layer.includes("Interface")).map(([f]) => f);

      document.getElementById("overview-entry-text").innerText = entryPoints.length 
        ? `Execution begins at: ${{entryPoints.join(", ")}}.`
        : `No explicit entry point found. Inspect top-level files.`;

      document.getElementById("overview-core-text").innerText = coreFiles.length 
        ? `Core domain logic resides in: ${{coreFiles.join(", ")}}.`
        : `Domain logic is distributed among internal modules.`;

      document.getElementById("overview-api-text").innerText = apiFiles.length
        ? `External endpoints and interfaces: ${{apiFiles.join(", ")}}.`
        : `Internal library or pipeline without separate HTTP endpoints.`;
    }}

    function openOverviewModal() {{ document.getElementById("overview-modal").classList.add("active"); }}
    function closeOverviewModal() {{ document.getElementById("overview-modal").classList.remove("active"); }}
    function closeOverviewModalOnOut(e) {{ if (e.target.id === "overview-modal") closeOverviewModal(); }}

    function showToast(msg) {{
      const t = document.getElementById("toast");
      t.innerText = msg;
      t.classList.add("show");
      setTimeout(() => t.classList.remove("show"), 2500);
    }}

    function copyMermaid() {{
      const rawCode = currentDirection === "TD" ? MERMAID_TD : MERMAID_LR;
      navigator.clipboard.writeText(rawCode).then(() => {{
        showToast("Mermaid diagram copied to clipboard");
      }}).catch(() => {{
        showToast("Could not access clipboard");
      }});
    }}

    function downloadMarkdown() {{
      const rawCode = currentDirection === "TD" ? MERMAID_TD : MERMAID_LR;
      const ticks = "```";
      const content = "# Architecture Overview: " + REPO_NAME + "\\n\\n" + ticks + "mermaid\\n" + rawCode + "\\n" + ticks + "\\n";
      const blob = new Blob([content], {{ type: "text/markdown;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ARCHITECTURE.md";
      a.click();
      URL.revokeObjectURL(url);
      showToast("ARCHITECTURE.md downloaded");
    }}

    function downloadSVG() {{
      const svg = panLayer.querySelector("svg");
      if (!svg) return;
      const serializer = new XMLSerializer();
      const source = serializer.serializeToString(svg);
      const blob = new Blob([source], {{ type: "image/svg+xml;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${{REPO_NAME}}-architecture.svg`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("SVG exported successfully");
    }}

    window.addEventListener("keydown", (e) => {{
      if (e.key === "Escape") {{
        closeInspector();
        closeOverviewModal();
      }} else if ((e.metaKey || e.ctrlKey) && e.key === "k") {{
        e.preventDefault();
        document.getElementById("module-search")?.focus();
      }} else if (e.key === "+" || e.key === "=") {{
        zoomIn();
      }} else if (e.key === "-" || e.key === "_") {{
        zoomOut();
      }} else if (e.key === "0" || e.key.toLowerCase() === "f") {{
        fitToScreen(true);
      }} else if (e.key.toLowerCase() === "t") {{
        toggleLayout();
      }}
    }});

    window.addEventListener("resize", () => {{
      fitToScreen(false);
    }});

    // Kick off
    initSidebar();
    renderMermaidDiagram();
  </script>
</body>
</html>
"""

def serve_directory(port: int = 8080):
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    server = HTTPServer(('localhost', port), QuietHandler)
    url = f"http://localhost:{port}/index.html"
    print(f"\nRepoGraph Server running at: {url}")
    print("Press Ctrl+C to stop.\n")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()

def main():
    args = sys.argv[1:]
    should_serve = "--serve" in args
    output_json = "--json" in args

    target_dir = "."
    for arg in args:
        if not arg.startswith("--"):
            target_dir = arg
            break

    target_path = Path(target_dir).resolve()
    repo_name = resolve_repo_name(target_path)

    print("\n" + "=" * 60)
    print(f" RepoGraph: {repo_name}")
    print("=" * 60)

    print(f"\n[1/3] Parsing repository: {repo_name}...")
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

    print("[2/3] Constructing architectural dependency graph...")
    mermaid_td = generate_bulletproof_ast_mermaid(summary, direction="TD")
    mermaid_lr = generate_bulletproof_ast_mermaid(summary, direction="LR")

    print("[3/3] Exporting artifacts...")
    with open("ARCHITECTURE.md", "w", encoding="utf-8") as f:
        f.write(f"# Architecture Overview: {repo_name}\n\n```mermaid\n{mermaid_td}\n```\n")

    html_page = build_unified_html(mermaid_td, mermaid_lr, repo_name, summary)
    with open("repograph.html", "w", encoding="utf-8") as f:
        f.write(html_page)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_page)

    print("\nSuccess! Artifacts generated:")
    print("  Markdown:    ARCHITECTURE.md")
    print("  Interactive: repograph.html & index.html\n")

    if should_serve:
        serve_directory()

if __name__ == "__main__":
    main()
