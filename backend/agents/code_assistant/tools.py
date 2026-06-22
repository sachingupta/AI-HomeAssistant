"""
Code Assistant Agent tools — read-only access to the local project filesystem.
These tools operate on source files and docs, NOT on Google Drive family data.
"""

import fnmatch
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Project root is two levels above this file: backend/agents/code_assistant/ → project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_EXCLUDE_DIRS = {".venv", "venv", "env", "node_modules", "__pycache__", ".git",
                 ".pytest_cache", "dist", "build", ".mypy_cache"}

_DOC_MAP = {
    "PRD":      "docs/PRD.md",
    "DESIGN":   "docs/DESIGN.md",
    "SECURITY": "docs/SECURITY.md",
    "LEARNING": "docs/LEARNING.md",
    "CLAUDE":   "CLAUDE.md",
}

_LOG_FILE = _PROJECT_ROOT / "backend" / "app.log"


def _safe_path(relative: str) -> Path:
    """Resolve a relative path and verify it stays inside the project root."""
    resolved = (_PROJECT_ROOT / relative).resolve()
    if not str(resolved).startswith(str(_PROJECT_ROOT)):
        raise ValueError(f"Path escapes project root: {relative!r}")
    return resolved


def read_file(path: str) -> dict:
    """Read a file from the project by relative path.

    Args:
        path: Path relative to project root (e.g. 'backend/main.py').

    Returns:
        dict with 'path', 'content', 'lines', or 'error'.
    """
    try:
        resolved = _safe_path(path)
    except ValueError as exc:
        return {"error": str(exc)}

    if not resolved.exists():
        return {"error": f"File not found: {path}"}
    if not resolved.is_file():
        return {"error": f"Not a file: {path}"}

    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content, "lines": content.count("\n") + 1}
    except OSError as exc:
        return {"error": str(exc)}


def list_files(directory: str = ".", pattern: str = "**/*.py") -> dict:
    """List project files matching a glob pattern, excluding build/venv dirs.

    Args:
        directory: Directory relative to project root to search in.
        pattern:   Glob pattern (e.g. '**/*.py', '**/*.ts', 'backend/**/*.py').

    Returns:
        dict with 'files' list and 'count'.
    """
    try:
        base = _safe_path(directory)
    except ValueError as exc:
        return {"error": str(exc)}

    if not base.exists():
        return {"error": f"Directory not found: {directory}"}

    matches: List[str] = []
    for p in base.glob(pattern):
        # Skip excluded directories anywhere in the path
        if any(part in _EXCLUDE_DIRS for part in p.parts):
            continue
        if p.is_file():
            matches.append(str(p.relative_to(_PROJECT_ROOT)))

    matches.sort()
    return {"files": matches, "count": len(matches)}


def search_code(query: str, directory: str = "backend", file_pattern: str = "*.py") -> dict:
    """Search for a string in source files (like grep).

    Args:
        query:        String to search for (case-insensitive).
        directory:    Directory relative to project root to search in.
        file_pattern: Glob pattern for filenames to search (e.g. '*.py', '*.ts').

    Returns:
        dict with 'matches' list (file, line, text) and 'total'. Capped at 50 results.
    """
    try:
        base = _safe_path(directory)
    except ValueError as exc:
        return {"error": str(exc)}

    if not base.exists():
        return {"error": f"Directory not found: {directory}"}

    query_lower = query.lower()
    matches: List[dict] = []

    for p in sorted(base.rglob(file_pattern)):
        if any(part in _EXCLUDE_DIRS for part in p.parts):
            continue
        if not p.is_file():
            continue
        try:
            for lineno, line in enumerate(
                p.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
            ):
                if query_lower in line.lower():
                    matches.append({
                        "file": str(p.relative_to(_PROJECT_ROOT)),
                        "line": lineno,
                        "text": line.rstrip(),
                    })
                    if len(matches) >= 50:
                        return {"matches": matches, "total": 50, "truncated": True}
        except OSError:
            continue

    return {"matches": matches, "total": len(matches), "truncated": False}


def read_doc(doc: str) -> dict:
    """Read a project documentation file by short name.

    Args:
        doc: One of 'PRD', 'DESIGN', 'SECURITY', 'LEARNING', 'CLAUDE'.

    Returns:
        dict with 'doc', 'path', 'content', or 'error'.
    """
    doc_upper = doc.upper()
    if doc_upper not in _DOC_MAP:
        known = ", ".join(sorted(_DOC_MAP.keys()))
        return {"error": f"Unknown doc {doc!r}. Known docs: {known}"}

    rel_path = _DOC_MAP[doc_upper]
    result = read_file(rel_path)
    if "error" in result:
        return result
    result["doc"] = doc_upper
    return result


def read_logs(lines: int = 50) -> dict:
    """Read the last N lines of the backend log file.

    Args:
        lines: Number of tail lines to return (default 50).

    Returns:
        dict with 'content' and 'lines_read', or a 'note' if no log file exists.
    """
    if not _LOG_FILE.exists():
        return {"content": "", "lines_read": 0, "note": "No log file found at backend/app.log"}

    try:
        all_lines = _LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {"content": "\n".join(tail), "lines_read": len(tail)}
    except OSError as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Claude tool schemas
# ---------------------------------------------------------------------------

CODE_ASSISTANT_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a project source file by its path relative to the project root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path, e.g. 'backend/main.py'"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List project files matching a glob pattern, excluding build/venv directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory relative to project root (default '.')"},
                "pattern":   {"type": "string", "description": "Glob pattern, e.g. '**/*.py' or 'backend/**/*.py'"},
            },
            "required": [],
        },
    },
    {
        "name": "search_code",
        "description": "Search for a string across source files (case-insensitive grep). Returns file, line number, and matching text. Capped at 50 results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":        {"type": "string", "description": "String to search for"},
                "directory":    {"type": "string", "description": "Directory to search in (default 'backend')"},
                "file_pattern": {"type": "string", "description": "Filename pattern (default '*.py')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_doc",
        "description": "Read a project documentation file. Valid names: PRD, DESIGN, SECURITY, LEARNING, CLAUDE.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc": {
                    "type": "string",
                    "enum": ["PRD", "DESIGN", "SECURITY", "LEARNING", "CLAUDE"],
                    "description": "Short name of the doc to read",
                },
            },
            "required": ["doc"],
        },
    },
    {
        "name": "read_logs",
        "description": "Read the last N lines of the backend application log file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lines": {"type": "integer", "description": "Number of log lines to return (default 50)"},
            },
            "required": [],
        },
    },
]

TOOL_REGISTRY = {
    "read_file":    read_file,
    "list_files":   list_files,
    "search_code":  search_code,
    "read_doc":     read_doc,
    "read_logs":    read_logs,
}
