#!/usr/bin/env python3
"""
Unit tests for RepoGraph.
Deterministic AST analysis, import resolution, cycle detection, and CLI parsing.
"""

import ast
import tempfile
import unittest
from pathlib import Path

from repograph import (
    sanitize_id,
    resolve_repo_name,
    classify_layer,
    detect_circular_dependencies,
    resolve_import_target,
    CodebaseVisitor,
    scan_repository,
    generate_bulletproof_ast_mermaid,
    parse_args,
    build_unified_html,
    GemmaArchitectEngine
)


class TestSanitizeId(unittest.TestCase):
    def test_basic_sanitize(self):
        self.assertEqual(sanitize_id("api/routes.py"), "api_routes_py")
        self.assertEqual(sanitize_id("my-service@v1"), "my_service_v1")

    def test_leading_digit(self):
        self.assertEqual(sanitize_id("123_module"), "n_123_module")

    def test_empty_string(self):
        self.assertEqual(sanitize_id(""), "node_root")


class TestResolveRepoName(unittest.TestCase):
    def test_custom_name(self):
        self.assertEqual(resolve_repo_name(Path("."), custom_name="CustomApp"), "CustomApp")

    def test_directory_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "cool_project"
            p.mkdir()
            self.assertEqual(resolve_repo_name(p), "cool_project")


class TestClassifyLayer(unittest.TestCase):
    def test_layers(self):
        visitor = CodebaseVisitor(Path("test.py"), Path("."))
        self.assertEqual(classify_layer("api/routes.py", visitor), "API & Interface")
        self.assertEqual(classify_layer("models/user.py", visitor), "Data & Storage")
        self.assertEqual(classify_layer("core/engine.py", visitor), "Core & Domain")
        self.assertEqual(classify_layer("utils/crypto.py", visitor), "Utilities & Shared")
        self.assertEqual(classify_layer("config/settings.py", visitor), "Configuration")

    def test_entry_point(self):
        visitor = CodebaseVisitor(Path("app.py"), Path("."))
        visitor.has_main = True
        self.assertEqual(classify_layer("app.py", visitor), "Application Entry")


class TestCircularDependencyDetection(unittest.TestCase):
    def test_no_cycles(self):
        summary = {
            "a.py": {"internal_dependencies": ["b.py"]},
            "b.py": {"internal_dependencies": ["c.py"]},
            "c.py": {"internal_dependencies": []}
        }
        self.assertEqual(detect_circular_dependencies(summary), [])

    def test_simple_cycle(self):
        summary = {
            "a.py": {"internal_dependencies": ["b.py"]},
            "b.py": {"internal_dependencies": ["a.py"]}
        }
        cycles = detect_circular_dependencies(summary)
        self.assertEqual(len(cycles), 1)
        self.assertIn("a.py", cycles[0])
        self.assertIn("b.py", cycles[0])

    def test_three_node_cycle(self):
        summary = {
            "a.py": {"internal_dependencies": ["b.py"]},
            "b.py": {"internal_dependencies": ["c.py"]},
            "c.py": {"internal_dependencies": ["a.py"]}
        }
        cycles = detect_circular_dependencies(summary)
        self.assertEqual(len(cycles), 1)
        self.assertEqual(len(cycles[0]), 4)  # [a, b, c, a] or rotation


class TestImportResolver(unittest.TestCase):
    def setUp(self):
        self.all_files = {
            "demo_project/app.py",
            "demo_project/api/routes.py",
            "demo_project/core/engine.py",
            "demo_project/models/user.py",
            "demo_project/utils/crypto.py"
        }

    def test_sibling_import_from_subfolder(self):
        target, ext = resolve_import_target(
            "demo_project/app.py", "api.routes", "APIRouter", 0, self.all_files
        )
        self.assertEqual(target, "demo_project/api/routes.py")
        self.assertIsNone(ext)

    def test_cross_folder_import(self):
        target, ext = resolve_import_target(
            "demo_project/api/routes.py", "models.user", "UserModel", 0, self.all_files
        )
        self.assertEqual(target, "demo_project/models/user.py")
        self.assertIsNone(ext)

    def test_external_third_party(self):
        target, ext = resolve_import_target(
            "demo_project/app.py", "requests", None, 0, self.all_files
        )
        self.assertIsNone(target)
        self.assertIsNotNone(ext)
        self.assertEqual(ext[0], "requests")
        self.assertEqual(ext[1], "third_party")

    def test_stdlib_package(self):
        target, ext = resolve_import_target(
            "demo_project/utils/crypto.py", "hashlib", None, 0, self.all_files
        )
        self.assertIsNone(target)
        self.assertIsNotNone(ext)
        self.assertEqual(ext[0], "hashlib")
        self.assertEqual(ext[1], "stdlib")


class TestCodebaseVisitor(unittest.TestCase):
    def test_class_and_method_extraction(self):
        code = '''
"""Sample module docstring."""
class Animal:
    """Base animal."""
    pass

class Dog(Animal):
    """A domestic canine."""
    def __init__(self, name: str):
        self.name = name

    def bark(self, volume: int = 5):
        pass

    async def fetch(self, item):
        pass

def global_helper(x, y):
    if x > y:
        return x
    return y
'''
        tree = ast.parse(code)
        visitor = CodebaseVisitor(Path("dog.py"), Path("."))
        visitor.visit(tree)

        self.assertIn("Animal", visitor.classes)
        self.assertIn("Dog", visitor.classes)
        self.assertEqual(visitor.class_details["Dog"]["bases"], ["Animal"])
        self.assertIn("bark(volume)", visitor.class_details["Dog"]["methods"])
        self.assertIn("async fetch(item)", visitor.class_details["Dog"]["methods"])
        self.assertIn("global_helper(x, y)", visitor.functions)
        self.assertEqual(visitor.docstring, "Sample module docstring.")


class TestScanDemoProject(unittest.TestCase):
    def test_scan_demo(self):
        demo_path = Path(__file__).resolve().parent.parent / "demo_project"
        if not demo_path.exists():
            self.skipTest("demo_project directory not found")

        summary = scan_repository(demo_path)
        self.assertGreaterEqual(len(summary), 6)
        self.assertIn("app.py", summary)
        self.assertIn("api/routes.py", summary["app.py"]["internal_dependencies"])

    def test_empty_init_cleanup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            (p / "pkg").mkdir()
            (p / "pkg" / "__init__.py").write_text("")
            (p / "pkg" / "real.py").write_text("def hello(): pass")
            summary = scan_repository(p)
            self.assertIn("pkg/real.py", summary)
            self.assertNotIn("pkg/__init__.py", summary)


class TestMermaidGeneration(unittest.TestCase):
    def test_mermaid_syntax(self):
        summary = {
            "app.py": {
                "id": "app_py",
                "layer": "Application Entry",
                "classes": ["Application"],
                "functions": [],
                "internal_dependencies": ["routes.py"],
                "has_entry_point": True
            },
            "routes.py": {
                "id": "routes_py",
                "layer": "API & Interface",
                "classes": ["Router"],
                "functions": [],
                "internal_dependencies": [],
                "has_entry_point": False
            }
        }
        mmd = generate_bulletproof_ast_mermaid(summary, direction="TD")
        self.assertIn("graph TD", mmd)
        self.assertIn("app_py --> routes_py", mmd)
        self.assertIn("subgraph layer_Application_Entry", mmd)


class TestGemmaArchitectEngine(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "app.py": {
                "id": "app_py",
                "layer": "Application Entry",
                "classes": ["Application"],
                "class_details": {"Application": {"bases": [], "methods": ["run()"]}},
                "functions": ["main()"],
                "internal_dependencies": ["api/routes.py"],
                "external_dependencies": [],
                "has_entry_point": True,
                "complexity": 5,
                "docstring": "Entrypoint of the app."
            },
            "api/routes.py": {
                "id": "api_routes_py",
                "layer": "API & Interface",
                "classes": ["RouterController"],
                "class_details": {"RouterController": {"bases": [], "methods": ["get()", "post()"]}},
                "functions": [],
                "internal_dependencies": ["core/engine.py"],
                "external_dependencies": [("requests", "third_party")],
                "has_entry_point": False,
                "complexity": 8,
                "docstring": "API Routing layer."
            },
            "core/engine.py": {
                "id": "core_engine_py",
                "layer": "Core & Domain",
                "classes": ["WorkflowEngine"],
                "class_details": {"WorkflowEngine": {"bases": [], "methods": ["compute()"]}},
                "functions": [],
                "internal_dependencies": ["models/user.py"],
                "external_dependencies": [],
                "has_entry_point": False,
                "complexity": 10,
                "docstring": "Business logic engine."
            },
            "models/user.py": {
                "id": "models_user_py",
                "layer": "Data & Storage",
                "classes": ["UserModel"],
                "class_details": {"UserModel": {"bases": [], "methods": ["find()", "save()"]}},
                "functions": [],
                "internal_dependencies": [],
                "external_dependencies": [],
                "has_entry_point": False,
                "complexity": 4,
                "docstring": "Data entity model."
            }
        }

    def test_gemma_architecture_analysis(self):
        result = GemmaArchitectEngine.analyze_architecture(
            summary=self.summary,
            cycles=[],
            repo_name="DemoApp",
            model="gemma2:2b",
            provider="offline"
        )
        self.assertIn("executive_summary", result)
        self.assertIn("design_patterns", result)
        self.assertIn("health_score", result)
        self.assertIn("modularity_analysis", result)
        self.assertIn("recommendations", result)
        self.assertIn("module_roles", result)
        self.assertEqual(result["health_score"], "A")
        
        # Test pattern detection
        pattern_names = [p["name"] for p in result["design_patterns"]]
        self.assertIn("Clean N-Tier Layered Architecture", pattern_names)
        self.assertIn("Dispatcher & Facade Pattern", pattern_names)
        self.assertIn("Core Domain Workflow Orchestrator", pattern_names)
        self.assertIn("Data Entity & Domain Model", pattern_names)

    def test_gemma_cycle_remediation_recipes(self):
        cycles = [["api/routes.py", "core/engine.py", "api/routes.py"]]
        result = GemmaArchitectEngine.analyze_architecture(
            summary=self.summary,
            cycles=cycles,
            repo_name="DemoApp"
        )
        self.assertEqual(result["health_score"], "C+")
        self.assertIn("circular_dependency_fixes", result)
        self.assertEqual(len(result["circular_dependency_fixes"]), 1)
        fix = result["circular_dependency_fixes"][0]
        self.assertIn("remediation_recipe", fix)
        self.assertIn("Dependency Inversion", fix["remediation_recipe"])

    def test_html_includes_gemma_analysis(self):
        ai_data = {
            "engine": "Google Gemma 2 (gemma2:2b)",
            "health_score": "A+",
            "executive_summary": "Top notch architecture.",
            "design_patterns": [{"name": "Facade", "description": "Unified interface"}],
            "modularity_analysis": "Decoupled.",
            "recommendations": ["Keep clean."],
            "circular_dependency_fixes": [],
            "module_roles": {"app.py": "Bootstrap"}
        }
        html = build_unified_html("graph TD\n", "graph LR\n", "DemoApp", self.summary, ai_analysis=ai_data)
        self.assertIn("Gemma AI Architect", html)
        self.assertIn("Top notch architecture.", html)
        self.assertIn("gemma-modal", html)



if __name__ == "__main__":
    unittest.main()

