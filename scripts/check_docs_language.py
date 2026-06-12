"""Keep project documentation in en-US.

Scans the en-US doc surface (``README.md``, ``CLAUDE.md``, ``docs/**``) for
running pt-BR prose. ``prompts.md`` is intentionally excluded: it is the Vibe
Coding audit log and quotes the architect's pt-BR prompts verbatim.

The threshold is generous so a stray brand name or quoted term does not trip it;
only a doc with several pt-BR markers fails. Bypass: ``FINOPS_DOCS_LANG_BYPASS=1``.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_THRESHOLD = 6

_PT_MARKERS = {
    "não",
    "você",
    "está",
    "também",
    "porque",
    "função",
    "código",
    "banco",
    "padrão",
    "sofrimento",
    "arquivo",
    "implementação",
    "configuração",
    "será",
    "então",
    "para",
    "com",
    "uma",
    "pra",
    "gente",
    "isso",
    "aqui",
    "fazer",
}

_WORD = re.compile(r"[a-zà-ú]+", re.IGNORECASE)


def _doc_files() -> list[Path]:
    files: list[Path] = []
    for name in ("README.md", "CLAUDE.md"):
        p = _REPO_ROOT / name
        if p.exists():
            files.append(p)
    docs = _REPO_ROOT / "docs"
    if docs.exists():
        files.extend(docs.rglob("*.md"))
    return files


def _pt_hits(text: str) -> int:
    words = [w.lower() for w in _WORD.findall(text)]
    return sum(1 for w in words if w in _PT_MARKERS)


def main() -> int:
    if os.environ.get("FINOPS_DOCS_LANG_BYPASS") == "1":
        print("check_docs_language: BYPASSED")
        return 0

    failures: list[str] = []
    for path in _doc_files():
        hits = _pt_hits(path.read_text(encoding="utf-8"))
        if hits >= _THRESHOLD:
            rel = path.relative_to(_REPO_ROOT).as_posix()
            failures.append(f"{rel}: {hits} pt-BR markers — project docs must be en-US")

    if failures:
        print("\n".join(failures))
        print(f"\ncheck_docs_language: {len(failures)} file(s)")
        return 1

    print("check_docs_language: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
