# Contributing to RepoGraph

Thank you for your interest in contributing to **RepoGraph**!

RepoGraph is built on a simple philosophy: **deterministic Abstract Syntax Tree (AST) analysis, instant execution, and zero third-party dependencies**.

---

## Development Setup

RepoGraph requires Python 3.9+ and zero external pip dependencies.

1. Clone the repository:
   ```bash
   git clone https://github.com/sharan-s-dev/RepoGraph-.git
   cd RepoGraph-
   ```

2. (Optional) Install in editable mode:
   ```bash
   python -m pip install -e .
   ```

---

## Running Tests

All contributions must pass the built-in test suite:

```bash
python -m unittest discover tests
```

To add new tests, place them in [`tests/test_repograph.py`](tests/test_repograph.py) using Python's standard `unittest` library.

---

## Testing Against the Demo Project

Verify blueprint and diagram generation:

```bash
python repograph.py demo_project -o ./output_test --name "demo_project"
```

Verify that:
- `output_test/ARCHITECTURE.md` is valid Mermaid markdown.
- `output_test/index.html` loads and renders properly in your browser.

---

## Pull Request Guidelines

1. Create a descriptive branch: `git checkout -b fix/issue-name` or `git checkout -b feat/feature-name`.
2. Keep dependencies at **zero external runtime dependencies**. Standard library only (`ast`, `argparse`, `json`, `os`, `re`, `sys`, `pathlib`).
3. Ensure all tests pass.
4. Submit a Pull Request with a clear description of changes.
