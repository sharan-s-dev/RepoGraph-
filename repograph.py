#!/usr/bin/env python3
"""
RepoGraph - Codebase Architecture & Dependency Graph Explorer
Deterministic AST dependency analysis + Interactive Web Blueprints.
Zero third-party pip dependencies required.
"""

import ast
import argparse
import json
import os
import re
import sys
import subprocess
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

__version__ = "1.0.0"

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Standard library modules set for classification
STDLIB_MODULES: Set[str] = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "collections", "concurrent",
    "contextlib", "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "enum", "errno", "fnmatch", "fractions", "functools", "gc", "glob", "gzip",
    "hashlib", "heapq", "hmac", "html", "http", "importlib", "inspect", "io", "itertools",
    "json", "logging", "math", "mimetypes", "multiprocessing", "operator", "os", "pathlib",
    "pickle", "platform", "pprint", "queue", "random", "re", "secrets", "select", "shutil",
    "signal", "socket", "sqlite3", "ssl", "stat", "string", "struct", "subprocess", "sys",
    "tempfile", "threading", "time", "traceback", "types", "typing", "unittest", "urllib",
    "uuid", "warnings", "weakref", "xml", "zipfile", "zlib"
}

IGNORED_DIRS: Set[str] = {
    ".git", "__pycache__", "venv", ".venv", "env", "node_modules",
    "dist", "build", ".idea", ".vscode", ".pytest_cache", "tests",
    ".eggs", "*.egg-info", ".mypy_cache", ".ruff_cache", "coverage", ".tox"
}


def sanitize_id(name: str) -> str:
    """Mermaid node IDs must strictly be alphanumeric and underscores."""
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    return cleaned or "node_root"


def resolve_repo_name(target_path: Path, custom_name: Optional[str] = None) -> str:
    """Intelligently determine a clean, professional project name."""
    if custom_name and custom_name.strip():
        return custom_name.strip()

    target_path = target_path.resolve()

    # 1. Check pyproject.toml / setup.cfg in target_path
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

    # 2. Check if target_path is itself a git repository root
    if (target_path / ".git").exists():
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

    # 3. Use directory name
    dir_name = target_path.name
    if dir_name and dir_name != ".":
        clean = re.sub(r'[-_]+$', '', dir_name)
        if clean:
            return clean

    return "RepoGraph"


class CodebaseVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, repo_root: Path):
        self.file_path = file_path
        self.repo_root = repo_root
        self.classes: List[str] = []
        self.class_details: Dict[str, Dict[str, Any]] = {}
        self.functions: List[str] = []
        self.raw_imports: List[Tuple[str, Optional[str], int]] = []
        self.docstring: str = ""
        self.full_docstring: str = ""
        self.has_main: bool = False
        self.complexity_score: int = 1

    def visit_Module(self, node: ast.Module):
        doc = ast.get_docstring(node)
        if doc:
            self.full_docstring = doc.strip()
            self.docstring = self.full_docstring.split("\n")[0][:140]
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith("__"):
                    args_list = [a.arg for a in item.args.args if a.arg != "self"]
                    is_async = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                    methods.append(f"{is_async}{item.name}({', '.join(args_list[:3])})")

        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(f"{getattr(b.value, 'id', '')}.{b.attr}".lstrip("."))

        class_doc = ast.get_docstring(node) or ""
        self.class_details[node.name] = {
            "methods": methods[:8],
            "bases": bases,
            "docstring": class_doc.split("\n")[0][:100] if class_doc else ""
        }
        self.complexity_score += 2
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not node.name.startswith("_"):
            args_list = [a.arg for a in node.args.args if a.arg != "self"]
            self.functions.append(f"{node.name}({', '.join(args_list[:3])})")
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if not node.name.startswith("_"):
            args_list = [a.arg for a in node.args.args if a.arg != "self"]
            self.functions.append(f"async {node.name}({', '.join(args_list[:3])})")
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        if isinstance(node.test, ast.Compare):
            left = getattr(node.test.left, "id", None)
            if left == "__name__":
                self.has_main = True
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        self.complexity_score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        self.complexity_score += len(node.values) - 1
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.raw_imports.append((alias.name, None, 0))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        level = node.level or 0
        mod = node.module or ""
        for alias in node.names:
            self.raw_imports.append((mod, alias.name, level))


def classify_layer(rel_path: str, visitor: CodebaseVisitor) -> str:
    """Classifies a Python module into an architectural layer."""
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
    """Detects cycles in the internal dependency graph and deduplicates them."""
    cycles: List[List[str]] = []
    seen_canonical: Set[Tuple[str, ...]] = set()

    def dfs(node: str, path: List[str], rec_stack: Set[str]):
        rec_stack.add(node)
        path.append(node)

        deps = summary.get(node, {}).get("internal_dependencies", [])
        for dep in deps:
            if dep not in summary:
                continue
            if dep in rec_stack:
                cycle_start = path.index(dep)
                cycle = path[cycle_start:] + [dep]
                core = cycle[:-1]
                if len(core) >= 2:
                    min_idx = core.index(min(core))
                    canonical = tuple(core[min_idx:] + core[:min_idx])
                    if canonical not in seen_canonical:
                        seen_canonical.add(canonical)
                        cycles.append(cycle)
            elif dep not in path:
                dfs(dep, path, rec_stack)

        path.pop()
        rec_stack.remove(node)

    for mod in sorted(summary.keys()):
        dfs(mod, [], set())

    return cycles[:10]


def resolve_import_target(
    importer_rel_posix: str,
    mod_name: str,
    item_name: Optional[str],
    level: int,
    all_py_files: Set[str]
) -> Tuple[Optional[str], Optional[Tuple[str, str]]]:
    """
    Deterministically resolves an import statement to either:
    1. An internal repository file path (relative posix)
    2. An external / stdlib package descriptor
    """
    mod_path = mod_name.replace(".", "/") if mod_name else ""
    importer_p = Path(importer_rel_posix)
    candidates: List[Path] = []

    if level > 0:
        # Relative import
        curr = importer_p.parent
        for _ in range(level - 1):
            curr = curr.parent
        base = curr / mod_path if mod_path else curr
        candidates.extend([
            base.with_suffix(".py"),
            base / "__init__.py"
        ])
        if item_name:
            candidates.extend([
                (base / item_name).with_suffix(".py"),
                base / item_name / "__init__.py"
            ])
    else:
        # Absolute import - check potential source roots
        roots: List[Path] = []
        curr = importer_p.parent
        while curr != Path("."):
            roots.append(curr)
            curr = curr.parent
        roots.append(Path("."))

        for r in roots:
            base = r / mod_path if mod_path else r
            candidates.extend([
                base.with_suffix(".py"),
                base / "__init__.py"
            ])
            if item_name:
                candidates.extend([
                    (base / item_name).with_suffix(".py"),
                    base / item_name / "__init__.py"
                ])

    for c in candidates:
        posix_c = c.as_posix()
        if posix_c in all_py_files and posix_c != importer_rel_posix:
            return posix_c, None

    # Suffix fallback: matches packages inside subdirectories (e.g., src/pkg/mod)
    if mod_path:
        suffix = "/" + mod_path + ".py"
        matches = [f for f in all_py_files if (f.endswith(suffix) or f == mod_path + ".py") and f != importer_rel_posix]
        if matches:
            # Rank matches by proximity to importer directory
            matches.sort(key=lambda m: len(set(Path(m).parts) & set(importer_p.parts)), reverse=True)
            return matches[0], None

        if item_name:
            suffix_item = f"/{mod_path}/{item_name}.py"
            matches_item = [f for f in all_py_files if (f.endswith(suffix_item) or f == f"{mod_path}/{item_name}.py") and f != importer_rel_posix]
            if matches_item:
                matches_item.sort(key=lambda m: len(set(Path(m).parts) & set(importer_p.parts)), reverse=True)
                return matches_item[0], None

    # External or stdlib package classification
    if level == 0 and mod_name:
        top_pkg = mod_name.split(".")[0]
        if top_pkg:
            pkg_type = "stdlib" if top_pkg in STDLIB_MODULES else "third_party"
            return None, (top_pkg, pkg_type)

    return None, None


def scan_repository(repo_path: Path, extra_excludes: Optional[List[str]] = None) -> Dict[str, Any]:
    repo_path = repo_path.resolve()
    codebase_summary: Dict[str, Any] = {}
    excludes = set(IGNORED_DIRS)
    if extra_excludes:
        excludes.update(extra_excludes)

    py_files: List[Path] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]
        for file in files:
            if file.endswith(".py"):
                full_p = Path(root) / file
                rel_parts = full_p.relative_to(repo_path).parts
                if not any(ex in rel_parts for ex in excludes):
                    py_files.append(full_p)

    all_py_files: Set[str] = {p.relative_to(repo_path).as_posix() for p in py_files}
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
                "full_docstring": visitor.full_docstring or visitor.docstring or "Python module",
                "classes": visitor.classes,
                "class_details": visitor.class_details,
                "functions": visitor.functions[:10],
                "all_functions_count": len(visitor.functions),
                "internal_dependencies": [],
                "external_dependencies": [],
                "stdlib_dependencies": [],
                "has_entry_point": visitor.has_main or rel_posix.endswith(("main.py", "app.py", "cli.py")),
                "loc": loc,
                "complexity": min(visitor.complexity_score, 100),
                "imported_by": []
            }
        except Exception:
            continue

    # Second pass: resolve dependencies
    for rel_posix, visitor in visitors.items():
        if rel_posix not in codebase_summary:
            continue

        internal_deps: Set[str] = set()
        external_deps: Set[str] = set()
        stdlib_deps: Set[str] = set()

        for mod_name, item_name, level in visitor.raw_imports:
            internal_target, ext_info = resolve_import_target(
                rel_posix, mod_name, item_name, level, all_py_files
            )
            if internal_target:
                internal_deps.add(internal_target)
            elif ext_info:
                pkg_name, pkg_type = ext_info
                if pkg_type == "stdlib":
                    stdlib_deps.add(pkg_name)
                else:
                    external_deps.add(pkg_name)

        codebase_summary[rel_posix]["internal_dependencies"] = sorted(list(internal_deps))
        codebase_summary[rel_posix]["external_dependencies"] = sorted(list(external_deps))
        codebase_summary[rel_posix]["stdlib_dependencies"] = sorted(list(stdlib_deps))

    # Third pass: compute imported_by
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


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RepoGraph - __REPO_NAME__ | Codebase Architecture Explorer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    :root {
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
      --crimson: #ef4444;
      --indigo: #818cf8;
      --font-ui: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-ui);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    header.top-nav {
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
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-badge {
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
    }

    .title-group h1 {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.2px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .title-group p {
      font-size: 11px;
      color: var(--text-muted);
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-pill {
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
    }

    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 8px var(--emerald);
    }

    .cycle-pill-nav {
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      font-family: var(--font-mono);
      transition: all 0.2s ease;
    }

    .cycle-pill-warn {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #fca5a5;
    }
    .cycle-pill-warn:hover {
      background: rgba(239, 68, 68, 0.3);
      border-color: #ef4444;
      color: #ffffff;
    }

    .cycle-pill-ok {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #6ee7b7;
    }

    .btn {
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
    }

    .btn:hover {
      background: #1e293b;
      border-color: var(--accent);
      color: #ffffff;
    }

    .btn-primary {
      background: linear-gradient(135deg, #0284c7, #2563eb);
      border: 1px solid #38bdf8;
      color: #ffffff;
      font-weight: 600;
    }

    .btn-primary:hover {
      background: linear-gradient(135deg, #0369a1, #1d4ed8);
      box-shadow: 0 0 14px var(--accent-glow);
    }

    .workspace {
      flex: 1;
      display: flex;
      position: relative;
      overflow: hidden;
    }

    aside.sidebar {
      width: 320px;
      background: rgba(12, 17, 29, 0.9);
      backdrop-filter: blur(12px);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 20;
      flex-shrink: 0;
    }

    .sidebar-header {
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
    }

    .search-box {
      position: relative;
      width: 100%;
    }

    .search-box input {
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
    }

    .search-box input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }

    .search-box .search-icon {
      position: absolute;
      left: 9px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 12px;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      padding: 10px 14px;
      background: rgba(9, 13, 22, 0.6);
      border-bottom: 1px solid var(--border);
    }

    .metric-card {
      background: var(--bg-surface-elevated);
      padding: 6px 8px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.04);
      text-align: center;
    }

    .metric-card .label {
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    .metric-card .value {
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      font-family: var(--font-mono);
      margin-top: 1px;
    }

    .cycle-alert-bar {
      margin: 8px 12px 2px;
      padding: 7px 10px;
      border-radius: 6px;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.35);
      color: #fca5a5;
      font-size: 11.5px;
      font-weight: 500;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
      transition: all 0.2s;
    }
    .cycle-alert-bar:hover {
      background: rgba(239, 68, 68, 0.25);
      border-color: #ef4444;
      color: #ffffff;
    }

    .layer-filters {
      padding: 8px 14px 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      border-bottom: 1px solid var(--border);
    }

    .layer-chip {
      font-size: 10.5px;
      font-weight: 500;
      padding: 2px 7px;
      border-radius: 12px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .layer-chip:hover, .layer-chip.active {
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--accent);
      color: #ffffff;
    }

    .module-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px 10px;
    }

    .module-item {
      padding: 8px 10px;
      margin-bottom: 5px;
      background: var(--bg-surface-elevated);
      border: 1px solid transparent;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .module-item:hover, .module-item.selected {
      background: #1e293b;
      border-color: var(--accent);
      transform: translateX(2px);
    }

    .module-title {
      font-size: 12.5px;
      font-weight: 600;
      color: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }

    .module-sub {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tag-badge {
      font-size: 9.5px;
      font-weight: 600;
      padding: 1px 5px;
      border-radius: 4px;
      background: rgba(56, 189, 248, 0.1);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.2);
    }

    main.viewport {
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
    }

    main.viewport.is-dragging {
      cursor: grabbing;
    }

    #pan-layer {
      position: absolute;
      top: 0;
      left: 0;
      transform-origin: 0 0;
      will-change: transform;
      pointer-events: auto;
    }

    #pan-layer svg {
      display: block;
      overflow: visible;
      filter: drop-shadow(0 10px 30px rgba(0, 0, 0, 0.5));
    }

    .viewport-controls {
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
    }

    .zoom-badge {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-muted);
      padding: 0 6px;
      min-width: 44px;
      text-align: center;
    }

    .control-btn {
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
    }

    .control-btn:hover {
      background: #1e293b;
      border-color: var(--accent);
      color: var(--accent);
    }

    .hint-chip {
      position: absolute;
      bottom: 14px;
      left: 14px;
      background: rgba(12, 17, 29, 0.9);
      backdrop-filter: blur(8px);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 11.5px;
      color: var(--text-muted);
      border: 1px solid var(--border);
      pointer-events: none;
      z-index: 30;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .legend-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 4px;
    }

    aside.inspector {
      width: 360px;
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
    }

    aside.inspector.open {
      transform: translateX(0);
    }

    .inspector-header {
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .inspector-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .section-title {
      font-size: 10.5px;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--text-muted);
      margin-bottom: 6px;
      font-weight: 600;
    }

    .class-card {
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      margin-bottom: 6px;
    }

    .class-header {
      font-size: 12px;
      font-family: var(--font-mono);
      color: #f8fafc;
      margin-bottom: 4px;
    }

    .class-kw {
      color: #38bdf8;
      font-weight: 600;
    }

    .class-bases {
      color: #94a3b8;
      font-size: 11px;
    }

    .class-methods {
      margin-top: 4px;
      padding-left: 8px;
      border-left: 2px solid #1e293b;
    }

    .method-sig {
      font-size: 11px;
      font-family: var(--font-mono);
      color: #cbd5e1;
      margin: 2px 0;
    }

    .symbol-pill {
      display: inline-block;
      padding: 3px 7px;
      margin: 2px 3px 3px 0;
      border-radius: 4px;
      background: #1e293b;
      border: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 11px;
      font-family: var(--font-mono);
      color: #38bdf8;
    }

    .ext-pill {
      display: inline-block;
      padding: 3px 8px;
      margin: 2px 4px 4px 0;
      border-radius: 4px;
      background: rgba(129, 140, 248, 0.15);
      border: 1px solid rgba(129, 140, 248, 0.3);
      font-size: 11px;
      font-family: var(--font-mono);
      color: #c7d2fe;
    }

    .stdlib-pill {
      display: inline-block;
      padding: 2px 6px;
      margin: 2px 3px 3px 0;
      border-radius: 4px;
      background: rgba(148, 163, 184, 0.1);
      border: 1px solid rgba(148, 163, 184, 0.2);
      font-size: 10.5px;
      font-family: var(--font-mono);
      color: #94a3b8;
    }

    .dep-link {
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
    }

    .dep-link:hover {
      border-color: var(--accent);
      background: #131b2e;
    }

    /* Modals */
    .modal-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(3, 7, 18, 0.85);
      backdrop-filter: blur(8px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .modal-overlay.active {
      display: flex;
    }

    .modal-dialog {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      max-width: 640px;
      width: 100%;
      max-height: 85vh;
      overflow-y: auto;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      padding: 20px;
      position: relative;
    }

    .modal-dialog h3 {
      font-size: 17px;
      margin-bottom: 4px;
    }

    .guide-step {
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 12px 14px;
      margin-top: 10px;
    }

    .guide-step h4 {
      font-size: 13px;
      color: var(--accent);
      margin-bottom: 3px;
    }

    .guide-step p {
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.45;
    }

    .cycle-card {
      background: #090d16;
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 6px;
      padding: 10px 12px;
      margin-top: 8px;
    }

    .cycle-chain {
      font-family: var(--font-mono);
      font-size: 11.5px;
      color: #fca5a5;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
      line-height: 1.5;
    }

    #toast {
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
    }

    #toast.show {
      transform: translateY(0);
      opacity: 1;
    }
  </style>
</head>
<body>

  <header class="top-nav">
    <div class="brand-group">
      <div class="logo-badge">RG</div>
      <div class="title-group">
        <h1>__REPO_NAME__</h1>
        <p>Codebase Architecture & Dependency Graph Explorer</p>
      </div>
    </div>

    <div class="nav-actions">
      <div class="status-pill">
        <span class="status-dot"></span>
        <span>Deterministic AST Engine</span>
      </div>

      <div id="cycles-nav-badge"></div>

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
          <div class="value">__TOTAL_FILES__</div>
        </div>
        <div class="metric-card">
          <div class="label">Classes</div>
          <div class="value">__TOTAL_CLASSES__</div>
        </div>
        <div class="metric-card">
          <div class="label">Funcs</div>
          <div class="value">__TOTAL_FUNCS__</div>
        </div>
        <div class="metric-card">
          <div class="label">Edges</div>
          <div class="value">__TOTAL_DEPS__</div>
        </div>
      </div>

      <div id="cycles-sidebar-container"></div>

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
        <span><span class="legend-dot" style="background:#38bdf8;"></span>Selected</span>
        <span><span class="legend-dot" style="background:#10b981;"></span>Inbound Caller</span>
        <span><span class="legend-dot" style="background:#06b6d4;"></span>Outbound Dependency</span>
        <span>&bull; Drag to Pan &bull; Scroll to Zoom</span>
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
          <p style="font-size: 12.5px; color: var(--text-muted); line-height: 1.45;" id="insp-doc"></p>
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
          <div class="section-title">Classes & Methods</div>
          <div id="insp-classes"></div>
        </div>

        <div id="insp-functions-section">
          <div class="section-title">Public Functions</div>
          <div id="insp-functions"></div>
        </div>

        <div>
          <div class="section-title">Outbound Internal Dependencies</div>
          <div id="insp-deps"></div>
        </div>

        <div>
          <div class="section-title">Inbound Callers (Imported By)</div>
          <div id="insp-imported-by"></div>
        </div>

        <div id="insp-ext-section">
          <div class="section-title">External / Third-Party Packages</div>
          <div id="insp-ext"></div>
        </div>

        <div id="insp-stdlib-section">
          <div class="section-title">Standard Library Dependencies</div>
          <div id="insp-stdlib"></div>
        </div>
      </div>
    </aside>
  </div>

  <!-- Architecture Overview Modal -->
  <div class="modal-overlay" id="overview-modal" onclick="closeOverviewModalOnOut(event)">
    <div class="modal-dialog">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3>Architecture Overview: __REPO_NAME__</h3>
        <button class="control-btn" onclick="closeOverviewModal()">✕</button>
      </div>
      <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">
        Architectural layers and execution boundaries in <strong>__REPO_NAME__</strong>.
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

  <!-- Circular Dependencies Modal -->
  <div class="modal-overlay" id="cycles-modal" onclick="closeCyclesModalOnOut(event)">
    <div class="modal-dialog">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3 style="color:#f87171;">Circular Dependencies Detected</h3>
        <button class="control-btn" onclick="closeCyclesModal()">✕</button>
      </div>
      <p style="font-size: 12.5px; color: var(--text-muted); margin-top: 4px;">
        Circular import chains introduce runtime `ImportError` exceptions and tight architectural coupling.
      </p>

      <div id="cycles-list-container" style="margin-top: 12px;"></div>

      <div style="margin-top: 16px; text-align: right;">
        <button class="btn btn-primary" onclick="closeCyclesModal()">Close</button>
      </div>
    </div>
  </div>

  <div id="toast">Diagram copied to clipboard!</div>

  <script>
    const SUMMARY = __SUMMARY_JSON__;
    const CYCLES = __CYCLES_JSON__;
    const MERMAID_TD = __MERMAID_TD__;
    const MERMAID_LR = __MERMAID_LR__;
    const REPO_NAME = "__REPO_NAME__";

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

    function updateTransform(smooth = false) {
      if (smooth) {
        panLayer.style.transition = "transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)";
      } else {
        panLayer.style.transition = "none";
      }
      panLayer.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
      
      const zoomIndicator = document.getElementById("zoom-level");
      if (zoomIndicator) {
        zoomIndicator.innerText = Math.round(scale * 100) + "%";
      }
    }

    viewport.addEventListener("mousedown", (e) => {
      if (e.button !== 0 || e.target.closest(".viewport-controls") || e.target.closest(".hint-chip")) return;
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      viewport.classList.add("is-dragging");
    });

    window.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      updateTransform(false);
    });

    window.addEventListener("mouseup", () => {
      if (isDragging) {
        isDragging = false;
        viewport.classList.remove("is-dragging");
      }
    });

    viewport.addEventListener("wheel", (e) => {
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
    }, { passive: false });

    // Touch events for mobile & tablets
    let initialTouchDist = 0;
    let initialTouchScale = 1;

    viewport.addEventListener("touchstart", (e) => {
      if (e.touches.length === 1) {
        isDragging = true;
        startX = e.touches[0].clientX - translateX;
        startY = e.touches[0].clientY - translateY;
        viewport.classList.add("is-dragging");
      } else if (e.touches.length === 2) {
        isDragging = false;
        initialTouchDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        initialTouchScale = scale;
      }
    }, { passive: true });

    viewport.addEventListener("touchmove", (e) => {
      if (e.touches.length === 1 && isDragging) {
        translateX = e.touches[0].clientX - startX;
        translateY = e.touches[0].clientY - startY;
        updateTransform(false);
      } else if (e.touches.length === 2 && initialTouchDist > 0) {
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
      }
    }, { passive: true });

    viewport.addEventListener("touchend", () => {
      isDragging = false;
      initialTouchDist = 0;
      viewport.classList.remove("is-dragging");
    });

    function zoomIn() { zoomAtCenter(1.25); }
    function zoomOut() { zoomAtCenter(0.8); }

    function zoomAtCenter(factor) {
      const cx = viewport.clientWidth / 2;
      const cy = viewport.clientHeight / 2;
      const newScale = Math.min(Math.max(scale * factor, 0.15), 6.0);
      translateX = cx - (cx - translateX) * (newScale / scale);
      translateY = cy - (cy - translateY) * (newScale / scale);
      scale = newScale;
      updateTransform(true);
    }

    function resetZoom() { fitToScreen(true); }

    function fitToScreen(smooth = true) {
      const svgEl = panLayer.querySelector("svg");
      if (!svgEl) return;
      
      const vpW = viewport.clientWidth;
      const vpH = viewport.clientHeight;
      if (vpW <= 0 || vpH <= 0) return;

      let svgW = 800;
      let svgH = 600;

      if (svgEl.viewBox && svgEl.viewBox.baseVal && svgEl.viewBox.baseVal.width > 0) {
        svgW = svgEl.viewBox.baseVal.width;
        svgH = svgEl.viewBox.baseVal.height;
      } else {
        try {
          const bbox = svgEl.getBBox();
          if (bbox.width > 0) {
            svgW = bbox.width;
            svgH = bbox.height;
          }
        } catch(e) {}
      }

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
      scale = Math.min(Math.max(scale, 0.2), 1.25);

      translateX = (vpW - svgW * scale) / 2;
      translateY = (vpH - svgH * scale) / 2;

      updateTransform(smooth);
    }

    function toggleLayout() {
      currentDirection = currentDirection === "TD" ? "LR" : "TD";
      renderMermaidDiagram();
      showToast("Switched to " + (currentDirection === "TD" ? "Top-Down" : "Left-to-Right") + " view");
    }

    // --- MERMAID RENDERING & BIDIRECTIONAL PATHWAY LIGHTING ---
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      themeVariables: {
        darkMode: true,
        background: '#06080e',
        primaryColor: '#0284c7',
        primaryTextColor: '#f8fafc',
        lineColor: '#38bdf8'
      }
    });

    async function renderMermaidDiagram() {
      panLayer.innerHTML = '<div style="color:var(--text-muted); font-size:13px; padding:20px;">Rendering architecture graph...</div>';
      try {
        const rawCode = currentDirection === "TD" ? MERMAID_TD : MERMAID_LR;
        const uniqueId = "mermaid_svg_" + Date.now();
        const { svg } = await mermaid.render(uniqueId, rawCode);
        panLayer.innerHTML = svg;

        const svgEl = panLayer.querySelector("svg");
        if (svgEl) {
          svgEl.style.maxWidth = "none";
          svgEl.style.display = "block";
          svgEl.removeAttribute("height");

          attachSvgNodeListeners();
          requestAnimationFrame(() => {
            fitToScreen(false);
          });
        }
      } catch (err) {
        console.error("Mermaid error:", err);
        panLayer.innerHTML = '<div style="color:var(--text-muted); font-size:13px; padding:20px;">Error rendering diagram.</div>';
      }
    }

    function attachSvgNodeListeners() {
      const svg = panLayer.querySelector("svg");
      if (!svg) return;

      const nodes = svg.querySelectorAll(".node");
      nodes.forEach(node => {
        node.style.cursor = "pointer";
        node.addEventListener("click", (e) => {
          e.stopPropagation();
          const cleanId = node.id.replace(/^flowchart-/, "").replace(/-[0-9]+$/, "");
          for (const [file, data] of Object.entries(SUMMARY)) {
            if (data.id === cleanId || node.id.includes(data.id)) {
              inspectModule(file);
              highlightNodeConnections(file);
              break;
            }
          }
        });
      });

      viewport.addEventListener("click", (e) => {
        if (!e.target.closest(".node") && !e.target.closest("#inspector-drawer") && !e.target.closest(".module-item")) {
          resetHighlights();
        }
      });
    }

    // TRUE PATHWAY LIGHTING: Selected = Blue, Inbound = Emerald Green, Outbound = Cyan
    function highlightNodeConnections(fileOrId) {
      const svg = panLayer.querySelector("svg");
      if (!svg) return;

      let targetData = SUMMARY[fileOrId];
      if (!targetData) {
        targetData = Object.values(SUMMARY).find(d => d.id === fileOrId);
      }
      if (!targetData) return;

      const targetId = targetData.id;
      const inboundIds = new Set((targetData.imported_by || []).map(f => SUMMARY[f]?.id).filter(Boolean));
      const outboundIds = new Set((targetData.internal_dependencies || []).map(f => SUMMARY[f]?.id).filter(Boolean));

      const nodes = svg.querySelectorAll(".node");
      const edges = svg.querySelectorAll(".edgePath, .edgeLabel");

      nodes.forEach(n => {
        const nId = n.id || "";
        const shape = n.querySelector("rect, polygon, circle, path");

        if (nId.includes(targetId)) {
          // Selected Node
          n.style.opacity = "1";
          n.style.filter = "drop-shadow(0 0 12px #38bdf8)";
          if (shape) {
            shape.style.stroke = "#38bdf8";
            shape.style.strokeWidth = "2.5px";
          }
        } else if (Array.from(inboundIds).some(id => nId.includes(id))) {
          // Inbound Callers -> Emerald Green
          n.style.opacity = "1";
          n.style.filter = "drop-shadow(0 0 10px #10b981)";
          if (shape) {
            shape.style.stroke = "#10b981";
            shape.style.strokeWidth = "2.5px";
          }
        } else if (Array.from(outboundIds).some(id => nId.includes(id))) {
          // Outbound Dependencies -> Cyan
          n.style.opacity = "1";
          n.style.filter = "drop-shadow(0 0 10px #06b6d4)";
          if (shape) {
            shape.style.stroke = "#06b6d4";
            shape.style.strokeWidth = "2.5px";
          }
        } else {
          n.style.opacity = "0.15";
          n.style.filter = "none";
          if (shape) {
            shape.style.stroke = "";
            shape.style.strokeWidth = "";
          }
        }
      });

      edges.forEach(e => {
        const eId = e.id || "";
        const pathEl = e.querySelector("path");

        const isInbound = Array.from(inboundIds).some(id => eId.includes(id) && eId.includes(targetId));
        const isOutbound = Array.from(outboundIds).some(id => eId.includes(id) && eId.includes(targetId));

        if (isInbound) {
          e.style.opacity = "1";
          if (pathEl) {
            pathEl.style.stroke = "#10b981";
            pathEl.style.strokeWidth = "2.5px";
          }
        } else if (isOutbound) {
          e.style.opacity = "1";
          if (pathEl) {
            pathEl.style.stroke = "#06b6d4";
            pathEl.style.strokeWidth = "2.5px";
          }
        } else {
          e.style.opacity = "0.08";
          if (pathEl) {
            pathEl.style.stroke = "";
            pathEl.style.strokeWidth = "";
          }
        }
      });
    }

    function highlightCycle(cycleNodes) {
      closeCyclesModal();
      const svg = panLayer.querySelector("svg");
      if (!svg) return;

      const cycleIds = new Set(cycleNodes.map(f => SUMMARY[f]?.id).filter(Boolean));
      const nodes = svg.querySelectorAll(".node");
      const edges = svg.querySelectorAll(".edgePath, .edgeLabel");

      nodes.forEach(n => {
        const nId = n.id || "";
        const shape = n.querySelector("rect, polygon, circle, path");
        if (Array.from(cycleIds).some(id => nId.includes(id))) {
          n.style.opacity = "1";
          n.style.filter = "drop-shadow(0 0 12px #ef4444)";
          if (shape) {
            shape.style.stroke = "#ef4444";
            shape.style.strokeWidth = "3px";
          }
        } else {
          n.style.opacity = "0.12";
          n.style.filter = "none";
          if (shape) {
            shape.style.stroke = "";
            shape.style.strokeWidth = "";
          }
        }
      });

      edges.forEach(e => {
        const eId = e.id || "";
        const pathEl = e.querySelector("path");
        const inCycle = Array.from(cycleIds).some(id1 => Array.from(cycleIds).some(id2 => id1 !== id2 && eId.includes(id1) && eId.includes(id2)));
        if (inCycle) {
          e.style.opacity = "1";
          if (pathEl) {
            pathEl.style.stroke = "#ef4444";
            pathEl.style.strokeWidth = "3px";
          }
        } else {
          e.style.opacity = "0.05";
        }
      });

      showToast("Highlighting circular dependency in red");
    }

    function resetHighlights() {
      const svg = panLayer.querySelector("svg");
      if (!svg) return;
      svg.querySelectorAll(".node, .edgePath, .edgeLabel").forEach(el => {
        el.style.opacity = "1";
        el.style.filter = "none";
        const shape = el.querySelector("rect, polygon, circle, path");
        if (shape) {
          shape.style.stroke = "";
          shape.style.strokeWidth = "";
        }
      });
    }

    function initSidebar() {
      const list = document.getElementById("module-list");
      const filterContainer = document.getElementById("layer-filters");
      const layers = new Set();

      list.innerHTML = "";
      for (const [file, data] of Object.entries(SUMMARY)) {
        layers.add(data.layer);

        const item = document.createElement("div");
        item.className = "module-item";
        item.id = `mod-item-${data.id}`;
        item.onclick = () => {
          inspectModule(file);
          highlightNodeConnections(file);
        };

        item.innerHTML = `
          <div class="module-title">
            <span style="overflow:hidden; text-overflow:ellipsis;">${file}</span>
            <span class="tag-badge">${data.layer.split(' ')[0]}</span>
          </div>
          <div class="module-sub">
            ${data.classes.length ? data.classes.join(', ') : (data.functions.slice(0,3).join(', ') || 'module')}
          </div>
        `;
        list.appendChild(item);
      }

      layers.forEach(layer => {
        const chip = document.createElement("span");
        chip.className = "layer-chip";
        chip.innerText = layer;
        chip.onclick = () => filterByLayer(layer);
        filterContainer.appendChild(chip);
      });

      initCyclesUI();
      populateOverviewModal();
    }

    function initCyclesUI() {
      const navBadge = document.getElementById("cycles-nav-badge");
      const sidebarContainer = document.getElementById("cycles-sidebar-container");
      const modalList = document.getElementById("cycles-list-container");

      if (CYCLES && CYCLES.length > 0) {
        navBadge.innerHTML = `
          <div class="cycle-pill-nav cycle-pill-warn" onclick="openCyclesModal()">
            <span>⚠️</span>
            <span>${CYCLES.length} Circular Dependencies</span>
          </div>
        `;

        sidebarContainer.innerHTML = `
          <div class="cycle-alert-bar" onclick="openCyclesModal()">
            <span>⚠️ ${CYCLES.length} Circular Imports Detected</span>
            <span style="font-size:10px; text-decoration:underline;">View</span>
          </div>
        `;

        modalList.innerHTML = CYCLES.map((cycle, i) => {
          const chainHtml = cycle.map((node, idx) => `
            <span>${node}</span>
            ${idx < cycle.length - 1 ? '<span style="color:#ef4444; font-weight:700;">➔</span>' : ''}
          `).join('');

          return `
            <div class="cycle-card">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:12px; font-weight:600; color:#fca5a5;">Cycle #${i+1} (${cycle.length - 1} steps)</span>
                <button class="btn" style="padding:2px 8px; font-size:10.5px;" onclick='highlightCycle(${JSON.stringify(cycle)})'>
                  Highlight in Graph
                </button>
              </div>
              <div class="cycle-chain">
                ${chainHtml}
              </div>
            </div>
          `;
        }).join('');
      } else {
        navBadge.innerHTML = `
          <div class="cycle-pill-nav cycle-pill-ok">
            <span>✓</span>
            <span>0 Circular Dependencies</span>
          </div>
        `;
        sidebarContainer.innerHTML = '';
      }
    }

    function filterByLayer(layer) {
      document.querySelectorAll(".layer-chip").forEach(c => {
        c.classList.toggle("active", c.innerText === layer || (layer === 'ALL' && c.innerText === 'All'));
      });

      for (const [file, data] of Object.entries(SUMMARY)) {
        const item = document.getElementById(`mod-item-${data.id}`);
        if (!item) continue;
        item.style.display = (layer === "ALL" || data.layer === layer) ? "block" : "none";
      }
    }

    function handleSearch(query) {
      const q = query.toLowerCase().trim();
      for (const [file, data] of Object.entries(SUMMARY)) {
        const item = document.getElementById(`mod-item-${data.id}`);
        if (!item) continue;
        const matches = file.toLowerCase().includes(q) ||
          data.classes.some(c => c.toLowerCase().includes(q)) ||
          data.functions.some(f => f.toLowerCase().includes(q)) ||
          data.layer.toLowerCase().includes(q);
        item.style.display = matches ? "block" : "none";
      }
    }

    function inspectModule(file) {
      const data = SUMMARY[file];
      if (!data) return;

      selectedModule = file;
      document.querySelectorAll(".module-item").forEach(i => i.classList.remove("selected"));
      const selItem = document.getElementById(`mod-item-${data.id}`);
      if (selItem) {
        selItem.classList.add("selected");
        selItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      document.getElementById("insp-file").innerText = file;
      document.getElementById("insp-layer").innerText = data.layer;
      document.getElementById("insp-doc").innerText = data.full_docstring || data.docstring || "No module docstring specified.";
      document.getElementById("insp-loc").innerText = data.loc;
      document.getElementById("insp-complexity").innerText = data.complexity;

      // Rich Class Details with Bases and Public Methods
      const clsContainer = document.getElementById("insp-classes");
      if (data.classes.length > 0) {
        document.getElementById("insp-classes-section").style.display = "block";
        clsContainer.innerHTML = data.classes.map(c => {
          const details = data.class_details?.[c];
          const bases = details?.bases?.length ? `(${details.bases.join(', ')})` : '';
          const methods = details?.methods?.length 
            ? details.methods.map(m => `<div class="method-sig"><code>${m}</code></div>`).join('') 
            : '<div style="font-size:11px; color:var(--text-faint); margin:2px 0;">No public methods</div>';

          return `
            <div class="class-card">
              <div class="class-header">
                <span class="class-kw">class</span> <strong style="color:#ffffff;">${c}</strong> <span class="class-bases">${bases}</span>
              </div>
              <div class="class-methods">
                ${methods}
              </div>
            </div>
          `;
        }).join("");
      } else {
        document.getElementById("insp-classes-section").style.display = "none";
      }

      // Public Functions
      const fnContainer = document.getElementById("insp-functions");
      if (data.functions.length > 0) {
        document.getElementById("insp-functions-section").style.display = "block";
        fnContainer.innerHTML = data.functions.map(f => `<span class="symbol-pill">${f}</span>`).join("");
      } else {
        document.getElementById("insp-functions-section").style.display = "none";
      }

      // Outbound Internal Dependencies
      const depsContainer = document.getElementById("insp-deps");
      if (data.internal_dependencies.length > 0) {
        depsContainer.innerHTML = data.internal_dependencies.map(d => `
          <div class="dep-link" onclick="inspectModule('${d}'); highlightNodeConnections('${d}');">
            <span>↳ ${d}</span>
            <span style="color:var(--accent);">inspect &rarr;</span>
          </div>
        `).join("");
      } else {
        depsContainer.innerHTML = `<span style="font-size:11.5px; color:var(--text-faint);">Standalone (No internal dependencies)</span>`;
      }

      // Inbound Callers
      const impByContainer = document.getElementById("insp-imported-by");
      if (data.imported_by && data.imported_by.length > 0) {
        impByContainer.innerHTML = data.imported_by.map(ib => `
          <div class="dep-link" onclick="inspectModule('${ib}'); highlightNodeConnections('${ib}');">
            <span>↲ ${ib}</span>
            <span style="color:var(--emerald);">imported by &rarr;</span>
          </div>
        `).join("");
      } else {
        impByContainer.innerHTML = `<span style="font-size:11.5px; color:var(--text-faint);">Not imported by internal modules</span>`;
      }

      // External Dependencies
      const extContainer = document.getElementById("insp-ext");
      if (data.external_dependencies && data.external_dependencies.length > 0) {
        document.getElementById("insp-ext-section").style.display = "block";
        extContainer.innerHTML = data.external_dependencies.map(e => `<span class="ext-pill">${e}</span>`).join("");
      } else {
        document.getElementById("insp-ext-section").style.display = "none";
      }

      // Standard Library
      const stdlibContainer = document.getElementById("insp-stdlib");
      if (data.stdlib_dependencies && data.stdlib_dependencies.length > 0) {
        document.getElementById("insp-stdlib-section").style.display = "block";
        stdlibContainer.innerHTML = data.stdlib_dependencies.map(s => `<span class="stdlib-pill">${s}</span>`).join("");
      } else {
        document.getElementById("insp-stdlib-section").style.display = "none";
      }

      document.getElementById("inspector-drawer").classList.add("open");
    }

    function closeInspector() {
      document.getElementById("inspector-drawer").classList.remove("open");
      document.querySelectorAll(".module-item").forEach(i => i.classList.remove("selected"));
      resetHighlights();
    }

    function populateOverviewModal() {
      const entryPoints = Object.entries(SUMMARY).filter(([_, d]) => d.has_entry_point).map(([f]) => f);
      const coreFiles = Object.entries(SUMMARY).filter(([_, d]) => d.layer.includes("Core") || d.layer.includes("Domain")).map(([f]) => f);
      const apiFiles = Object.entries(SUMMARY).filter(([_, d]) => d.layer.includes("API") || d.layer.includes("Interface")).map(([f]) => f);

      document.getElementById("overview-entry-text").innerText = entryPoints.length 
        ? `Execution begins at: ${entryPoints.join(", ")}.`
        : `No explicit entry point found. Inspect top-level files.`;

      document.getElementById("overview-core-text").innerText = coreFiles.length 
        ? `Core domain logic resides in: ${coreFiles.join(", ")}.`
        : `Domain logic is distributed among internal modules.`;

      document.getElementById("overview-api-text").innerText = apiFiles.length
        ? `External endpoints and interfaces: ${apiFiles.join(", ")}.`
        : `Internal library or pipeline without separate HTTP endpoints.`;
    }

    function openOverviewModal() { document.getElementById("overview-modal").classList.add("active"); }
    function closeOverviewModal() { document.getElementById("overview-modal").classList.remove("active"); }
    function closeOverviewModalOnOut(e) { if (e.target.id === "overview-modal") closeOverviewModal(); }

    function openCyclesModal() { document.getElementById("cycles-modal").classList.add("active"); }
    function closeCyclesModal() { document.getElementById("cycles-modal").classList.remove("active"); }
    function closeCyclesModalOnOut(e) { if (e.target.id === "cycles-modal") closeCyclesModal(); }

    function showToast(msg) {
      const t = document.getElementById("toast");
      t.innerText = msg;
      t.classList.add("show");
      setTimeout(() => t.classList.remove("show"), 2500);
    }

    function copyMermaid() {
      const rawCode = currentDirection === "TD" ? MERMAID_TD : MERMAID_LR;
      navigator.clipboard.writeText(rawCode).then(() => {
        showToast("Mermaid diagram copied to clipboard");
      }).catch(() => {
        showToast("Could not access clipboard");
      });
    }

    function downloadMarkdown() {
      const rawCode = currentDirection === "TD" ? MERMAID_TD : MERMAID_LR;
      const ticks = "```";
      let content = "# Architecture Overview: " + REPO_NAME + "\\n\\n" + ticks + "mermaid\\n" + rawCode + "\\n" + ticks + "\\n";
      if (CYCLES && CYCLES.length > 0) {
        content += "\\n> [!WARNING]\\n> **Circular Dependencies Detected:**\\n";
        CYCLES.forEach((c, idx) => {
          content += "> - Cycle " + (idx + 1) + ": `" + c.join(" ➔ ") + "`\\n";
        });
      }
      const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ARCHITECTURE.md";
      a.click();
      URL.revokeObjectURL(url);
      showToast("ARCHITECTURE.md downloaded");
    }

    function downloadSVG() {
      const svg = panLayer.querySelector("svg");
      if (!svg) return;
      const clone = svg.cloneNode(true);
      clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");

      const styleEl = document.createElement("style");
      styleEl.textContent = `
        .node rect, .node circle, .node ellipse, .node polygon, .node path { fill: #0f172a; stroke: #64748b; stroke-width: 1.5px; }
        .node .label text, .node text { fill: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 13px; }
        .edgePath path { stroke: #38bdf8; stroke-width: 1.5px; fill: none; }
        .edgeLabel text { fill: #94a3b8; font-family: monospace; font-size: 11px; }
        .cluster rect { fill: #0b1120; stroke: #1e293b; stroke-width: 1px; stroke-dasharray: 4 4; }
        .cluster text { fill: #94a3b8; font-family: -apple-system, sans-serif; font-weight: 600; font-size: 12px; }
      `;
      clone.insertBefore(styleEl, clone.firstChild);

      const serializer = new XMLSerializer();
      let source = serializer.serializeToString(clone);
      if (!source.match(/^<svg[^>]+xmlns="http:\\/\\/www\\.w3\\.org\\/2000\\/svg"/)) {
        source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
      }
      const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${REPO_NAME}-architecture.svg`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("SVG exported successfully");
    }

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeInspector();
        closeOverviewModal();
        closeCyclesModal();
      } else if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        document.getElementById("module-search")?.focus();
      } else if (e.key === "+" || e.key === "=") {
        zoomIn();
      } else if (e.key === "-" || e.key === "_") {
        zoomOut();
      } else if (e.key === "0" || e.key.toLowerCase() === "f") {
        fitToScreen(true);
      } else if (e.key.toLowerCase() === "t") {
        toggleLayout();
      } else if (e.key.toLowerCase() === "c" && CYCLES.length > 0) {
        openCyclesModal();
      }
    });

    window.addEventListener("resize", () => {
      fitToScreen(false);
    });

    initSidebar();
    renderMermaidDiagram();
  </script>
</body>
</html>
"""


def build_unified_html(mermaid_td: str, mermaid_lr: str, repo_name: str, summary: Dict[str, Any]) -> str:
    summary_json = json.dumps(summary, indent=None)
    cycles = detect_circular_dependencies(summary)
    cycles_json = json.dumps(cycles)

    total_files = len(summary)
    total_classes = sum(len(d["classes"]) for d in summary.values())
    total_functions = sum(d["all_functions_count"] for d in summary.values())
    total_loc = sum(d["loc"] for d in summary.values())
    total_deps = sum(len(d["internal_dependencies"]) for d in summary.values())

    content = HTML_TEMPLATE
    replacements = {
        "__REPO_NAME__": repo_name,
        "__SUMMARY_JSON__": summary_json,
        "__CYCLES_JSON__": cycles_json,
        "__MERMAID_TD__": json.dumps(mermaid_td),
        "__MERMAID_LR__": json.dumps(mermaid_lr),
        "__TOTAL_FILES__": str(total_files),
        "__TOTAL_CLASSES__": str(total_classes),
        "__TOTAL_FUNCS__": str(total_functions),
        "__TOTAL_DEPS__": str(total_deps),
        "__TOTAL_LOC__": str(total_loc),
        "__CYCLES_COUNT__": str(len(cycles))
    }

    for placeholder, val in replacements.items():
        content = content.replace(placeholder, val)

    return content


def serve_directory(port: int = 8080, target_dir: str = ".", open_browser: bool = True):
    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=target_dir, **kwargs)

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("localhost", port), QuietHandler)
    url = f"http://localhost:{port}/index.html"
    print(f"\nRepoGraph Server running at: {url}")
    print("Press Ctrl+C to stop.\n")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


def parse_args():
    parser = argparse.ArgumentParser(
        prog="repograph",
        description="RepoGraph: Fast, deterministic codebase architecture & dependency graph explorer for Python."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Path to Python repository or directory to analyze (default: current directory)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory to place generated files (default: current working directory)"
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Custom project name to display (overrides auto-detection)"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Launch a lightweight local HTTP server and open the blueprint in your browser"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for the local HTTP server (default: 8080)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically when --serve is used"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw codebase summary as JSON to stdout instead of generating HTML"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Additional directories, files, or patterns to exclude from analysis"
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip generating HTML blueprint (only generate ARCHITECTURE.md)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    target_path = Path(args.target).resolve()
    if not target_path.exists():
        print(f"Error: Target path does not exist: {target_path}")
        sys.exit(1)

    output_dir = Path(args.output).resolve() if args.output else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_name = resolve_repo_name(target_path, args.name)

    print("\n" + "=" * 60)
    print(f" RepoGraph: {repo_name}")
    print("=" * 60)

    print(f"\n[1/3] Parsing repository: {target_path}...")
    summary = scan_repository(target_path, extra_excludes=args.exclude)

    if not summary:
        print(f"[!] No Python files found in: {target_path}")
        sys.exit(1)

    total_classes = sum(len(d["classes"]) for d in summary.values())
    total_funcs = sum(d["all_functions_count"] for d in summary.values())
    total_deps = sum(len(d["internal_dependencies"]) for d in summary.values())
    cycles = detect_circular_dependencies(summary)

    print(f"      Parsed {len(summary)} modules, {total_classes} classes, {total_funcs} functions, {total_deps} edges.")
    if cycles:
        print(f"      [!] Warning: {len(cycles)} circular dependencies detected!")

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print("[2/3] Constructing architectural dependency graph...")
    mermaid_td = generate_bulletproof_ast_mermaid(summary, direction="TD")
    mermaid_lr = generate_bulletproof_ast_mermaid(summary, direction="LR")

    print("[3/3] Exporting artifacts to: " + str(output_dir) + "...")
    arch_md_path = output_dir / "ARCHITECTURE.md"
    with open(arch_md_path, "w", encoding="utf-8") as f:
        f.write(f"# Architecture Overview: {repo_name}\n\n```mermaid\n{mermaid_td}\n```\n")
        if cycles:
            f.write("\n## Circular Dependencies\n\n> [!WARNING]\n> The following circular import chains were detected:\n")
            for idx, c in enumerate(cycles, 1):
                f.write(f"> - **Cycle {idx}**: `{' ➔ '.join(c)}`\n")

    if not args.no_html:
        html_page = build_unified_html(mermaid_td, mermaid_lr, repo_name, summary)
        repograph_html_path = output_dir / "repograph.html"
        index_html_path = output_dir / "index.html"
        with open(repograph_html_path, "w", encoding="utf-8") as f:
            f.write(html_page)
        with open(index_html_path, "w", encoding="utf-8") as f:
            f.write(html_page)

    print("\nSuccess! Artifacts generated:")
    print(f"  Markdown:    {arch_md_path}")
    if not args.no_html:
        print(f"  Interactive: {output_dir / 'index.html'} & {output_dir / 'repograph.html'}\n")

    if args.serve:
        serve_directory(port=args.port, target_dir=str(output_dir), open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
