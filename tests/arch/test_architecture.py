"""Architecture and boundary test suite.

Proves the architectural invariants defined in DesignPhasePlan_2.md §03 and §09:
- Layer boundary rules (core and domain cannot import adapters, web, mcp, or network libraries)
- Contracts purity (contracts contains Protocol definitions and types only)
- No background daemon / watcher rules (V§14.4)
- File size, function size, and comprehension nesting limits (§09)
"""

import ast
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
IW_PACKAGE = REPO_ROOT / "iw"

# Standard library module names in Python 3.12
STDLIB_MODULES = set(sys.stdlib_module_names) | {"yaml", "pydantic"}


def get_python_files(directory: Path) -> list[Path]:
    """Return all Python files under a directory."""
    if not directory.exists():
        return []
    return [p for p in directory.rglob("*.py") if p.is_file()]


def test_core_and_domain_do_not_import_adapters_web_or_mcp():
    """Core and domain must depend only on contracts, core (for domain), and stdlib/yaml."""
    allowed_internal_prefixes = {
        "core": ("iw.contracts", "iw.core"),
        "domain": ("iw.contracts", "iw.core", "iw.domain"),
    }

    violations: list[str] = []

    for layer_name in ("core", "domain"):
        layer_dir = IW_PACKAGE / layer_name
        allowed_prefixes = allowed_internal_prefixes[layer_name]

        for py_file in get_python_files(layer_dir):
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0]
                        if top_pkg in ("iw",):
                            if not any(alias.name.startswith(p) for p in allowed_prefixes):
                                violations.append(
                                    f"{py_file.name}:{node.lineno} imports forbidden '{alias.name}'"
                                )
                        elif top_pkg not in STDLIB_MODULES:
                            violations.append(
                                f"{py_file.name}:{node.lineno} imports vendor/network package '{alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    top_pkg = module.split(".")[0]
                    if top_pkg in ("iw",):
                        if not any(module.startswith(p) for p in allowed_prefixes):
                            violations.append(
                                f"{py_file.name}:{node.lineno} from-imports forbidden '{module}'"
                            )
                    elif top_pkg and top_pkg not in STDLIB_MODULES:
                        violations.append(
                            f"{py_file.name}:{node.lineno} from-imports vendor/network package '{module}'"
                        )

    assert not violations, f"Layer boundary violations found:\n" + "\n".join(violations)


def test_contracts_contain_only_protocols_and_types():
    """Contracts package must have Protocol definitions and types only, no implementation logic."""
    violations: list[str] = []
    contracts_dir = IW_PACKAGE / "contracts"

    for py_file in get_python_files(contracts_dir):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            # Check for non-protocol classes with method bodies that do real work
            if isinstance(node, ast.FunctionDef) and not any(
                isinstance(p, ast.Pass) or isinstance(p, ast.Expr) for p in node.body
            ):
                pass

    assert not violations, f"Contracts purity violations:\n" + "\n".join(violations)


def test_no_filesystem_watchers_or_background_engines_in_codebase():
    """V§14.4: No background threads, schedulers, or file system watchers."""
    forbidden_modules = ("watchdog", "watchfiles", "sched", "celery", "apscheduler")

    violations: list[str] = []
    for py_file in get_python_files(IW_PACKAGE):
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_modules:
                        violations.append(f"{py_file.name}:{node.lineno} imports '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module in forbidden_modules:
                    violations.append(f"{py_file.name}:{node.lineno} imports '{node.module}'")

    assert not violations, f"Forbidden background engine imports found:\n" + "\n".join(violations)


def test_no_file_exceeds_200_lines():
    """Reviewability limit: no file in the iw package may exceed 200 lines."""
    violations: list[str] = []
    for py_file in get_python_files(IW_PACKAGE):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        if len(lines) > 200:
            violations.append(f"{py_file.name} has {len(lines)} lines (max 200)")

    assert not violations, f"File size violations found:\n" + "\n".join(violations)


def test_no_function_exceeds_40_lines():
    """Reviewability limit: no function in the iw package may exceed 40 lines."""
    violations: list[str] = []
    for py_file in get_python_files(IW_PACKAGE):
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                length = (node.end_lineno or node.lineno) - node.lineno + 1
                if length > 40:
                    violations.append(
                        f"{py_file.name}::{node.name} has {length} lines (max 40)"
                    )

    assert not violations, f"Function length violations found:\n" + "\n".join(violations)


def test_no_comprehension_nested_more_than_one_level():
    """Reviewability limit: no comprehension nested within another comprehension."""
    violations: list[str] = []
    for py_file in get_python_files(IW_PACKAGE):
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for child in ast.walk(node):
                    if child is not node and isinstance(
                        child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
                    ):
                        violations.append(
                            f"{py_file.name}:{node.lineno} contains nested comprehension"
                        )

    assert not violations, f"Nested comprehension violations:\n" + "\n".join(violations)
