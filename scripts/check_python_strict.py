"""Tokenizer gate: ban suppression comments and broad ``except`` clauses.

This repo does not allow suppressing the linter (a ``noqa`` comment) or catching
``Exception`` / ``BaseException`` broadly. The fix is always to narrow the catch
to a named exception (or restructure), never to silence the tool.

It works on the token stream, not raw text, so a ``noqa`` or ``except Exception``
mentioned inside a docstring or string literal (as in this file's own
documentation) is not a false positive — only real comments and real code count.

Exit non-zero on any violation. Bypass with ``FINOPS_PY_STRICT_BYPASS=1``.
"""

from __future__ import annotations

import os
import re
import sys
import token
import tokenize
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCAN_DIRS = ("app", "scripts", "tests")

_NOQA = re.compile(r"#\s*noqa", re.IGNORECASE)
_BROAD = {"Exception", "BaseException"}


def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for d in _SCAN_DIRS:
        files.extend((_REPO_ROOT / d).rglob("*.py"))
    return files


def _check_tokens(path: Path) -> list[str]:
    rel = path.relative_to(_REPO_ROOT)
    out: list[str] = []
    with path.open("rb") as fh:
        tokens = list(tokenize.tokenize(fh.readline))

    for i, tok in enumerate(tokens):
        if tok.type == tokenize.COMMENT and _NOQA.search(tok.string):
            out.append(f"{rel}:{tok.start[0]}: a 'noqa' comment is banned — fix the lint instead")
        if tok.type == token.NAME and tok.string == "except":
            nxt = _next_significant(tokens, i + 1)
            if nxt is not None and nxt.type == token.NAME and nxt.string in _BROAD:
                out.append(f"{rel}:{tok.start[0]}: broad except — narrow to a named exception")

    return out


def _next_significant(tokens: list[tokenize.TokenInfo], start: int) -> tokenize.TokenInfo | None:
    """Return the next token that is not whitespace, a comment, or an open paren."""

    skip = {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}
    for j in range(start, len(tokens)):
        t = tokens[j]
        if t.type in skip:
            continue
        if t.type == token.OP and t.string == "(":
            continue
        return t
    return None


def main() -> int:
    if os.environ.get("FINOPS_PY_STRICT_BYPASS") == "1":
        print("check_python_strict: BYPASSED")
        return 0

    violations: list[str] = []
    for path in _iter_py_files():
        violations.extend(_check_tokens(path))

    if violations:
        print("\n".join(violations))
        print(f"\ncheck_python_strict: {len(violations)} violation(s)")
        return 1

    print("check_python_strict: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
