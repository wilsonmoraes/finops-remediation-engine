"""AST gate: enforce the layering contract from .claude/rules/layering.md.

Each rule is keyed on the file's path within ``app/``:

- ``modules/<name>/router.py``  — no ``app.db`` import; no ``BaseModel`` subclass.
- ``modules/<name>/service.py`` — no ``fastapi`` import.
- ``modules/<name>/repo.py``    — no ``fastapi`` import.
- ``detectors/**``              — pure: no ``app.db``/``fastapi``/cloud-SDK/HTTP/LLM imports.
- ``providers/*/remediation.py``— pure: no ``app.db``/cloud-SDK/HTTP/LLM imports.
- ``providers/*/parser.py``     — pure: no ``app.db``/``fastapi`` imports.

Exit non-zero on any violation. Bypass with ``FINOPS_MODULE_LAYERING_BYPASS=1``.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_APP = _REPO_ROOT / "app"

_CLOUD_HTTP_LLM = {
    "boto3",
    "httpx",
    "requests",
    "aiohttp",
    "urllib",
    "anthropic",
    "openai",
    "langchain",
}


def _imported_roots(tree: ast.Module) -> set[str]:
    """Return the set of top-level module names imported by the file."""

    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _imports_app_db(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name == "app.db" or a.name.startswith("app.db.") for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "app.db":
                return True
            if node.module == "app" and any(a.name == "db" for a in node.names):
                return True
    return False


def _imports_fastapi(tree: ast.Module) -> bool:
    return "fastapi" in _imported_roots(tree)


def _declares_basemodel_subclass(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseModel":
                    return True
                if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                    return True
    return False


def _forbidden_roots(tree: ast.Module, forbidden: set[str]) -> set[str]:
    return _imported_roots(tree) & forbidden


def _check_module(rel: str, name: str, tree: ast.Module) -> list[str]:
    out: list[str] = []
    if name == "router.py":
        if _imports_app_db(tree):
            out.append(f"{rel}: router.py must not import app.db — move the call into a repo")
        if _declares_basemodel_subclass(tree):
            out.append(f"{rel}: router.py must not declare a BaseModel — move it to schemas.py")
    if name in {"service.py", "repo.py"} and _imports_fastapi(tree):
        out.append(f"{rel}: {name} must not import fastapi — keep the HTTP boundary in router.py")
    return out


def _check_pure(rel: str, layer: str, tree: ast.Module, forbidden: set[str]) -> list[str]:
    out: list[str] = []
    if _imports_app_db(tree):
        out.append(f"{rel}: {layer} must be pure — no app.db import")
    bad = _forbidden_roots(tree, forbidden)
    if bad:
        out.append(f"{rel}: {layer} must be pure — forbidden import(s): {', '.join(sorted(bad))}")
    return out


def _check_file(path: Path) -> list[str]:
    rel = path.relative_to(_REPO_ROOT).as_posix()
    parts = path.relative_to(_APP).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    if "/modules/" in f"/{parts}":
        return _check_module(rel, path.name, tree)
    if parts.startswith("detectors/"):
        return _check_pure(rel, "detectors", tree, _CLOUD_HTTP_LLM | {"fastapi"})
    if parts.startswith("providers/") and path.name == "remediation.py":
        return _check_pure(rel, "remediation.py", tree, _CLOUD_HTTP_LLM)
    if parts.startswith("providers/") and path.name == "parser.py":
        return _check_pure(rel, "parser.py", tree, {"fastapi"})
    return []


def main() -> int:
    if os.environ.get("FINOPS_MODULE_LAYERING_BYPASS") == "1":
        print("check_module_layering: BYPASSED")
        return 0

    violations: list[str] = []
    for path in _APP.rglob("*.py"):
        violations.extend(_check_file(path))

    if violations:
        print("\n".join(violations))
        print(f"\ncheck_module_layering: {len(violations)} violation(s)")
        return 1

    print("check_module_layering: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
