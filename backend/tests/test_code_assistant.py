"""
Unit tests for Code Assistant Agent tools.
All filesystem access is mocked — no real files are read.
Run: pytest backend/tests/test_code_assistant.py -v
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from backend.agents.code_assistant.tools import (
    _PROJECT_ROOT,
    list_files,
    read_doc,
    read_file,
    read_logs,
    search_code,
)


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_reads_existing_file(self):
        fake_content = "def hello():\n    pass\n"
        m = mock_open(read_data=fake_content)
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True), \
             patch("pathlib.Path.read_text", return_value=fake_content):
            result = read_file("backend/main.py")
        assert result["content"] == fake_content
        assert result["lines"] == 3
        assert result["path"] == "backend/main.py"

    def test_missing_file_returns_error(self):
        with patch("pathlib.Path.exists", return_value=False):
            result = read_file("backend/nonexistent.py")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_path_escape_returns_error(self):
        result = read_file("../../etc/passwd")
        assert "error" in result
        assert "escapes" in result["error"].lower()

    def test_directory_path_returns_error(self):
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_file", return_value=False):
            result = read_file("backend")
        assert "error" in result
        assert "not a file" in result["error"].lower()


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

class TestListFiles:
    def _make_mock_paths(self, names):
        """Return mock Path objects that pass the _EXCLUDE_DIRS check."""
        mocks = []
        for name in names:
            p = MagicMock(spec=Path)
            p.parts = (_PROJECT_ROOT / name).parts
            p.is_file.return_value = True
            p.relative_to.return_value = Path(name)
            mocks.append(p)
        return mocks

    def test_returns_matching_files(self):
        files = self._make_mock_paths(["backend/main.py", "backend/config.py"])
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.glob", return_value=iter(files)):
            result = list_files("backend", "**/*.py")
        assert result["count"] == 2
        assert "backend/main.py" in result["files"]

    def test_excludes_venv_directory(self):
        venv_file = MagicMock(spec=Path)
        venv_file.parts = (_PROJECT_ROOT / ".venv" / "lib" / "site.py").parts
        venv_file.is_file.return_value = True

        good_file = MagicMock(spec=Path)
        good_file.parts = (_PROJECT_ROOT / "backend" / "main.py").parts
        good_file.is_file.return_value = True
        good_file.relative_to.return_value = Path("backend/main.py")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.glob", return_value=iter([venv_file, good_file])):
            result = list_files(".", "**/*.py")
        assert result["count"] == 1
        assert "backend/main.py" in result["files"]

    def test_missing_directory_returns_error(self):
        with patch("pathlib.Path.exists", return_value=False):
            result = list_files("nonexistent")
        assert "error" in result

    def test_path_escape_returns_error(self):
        result = list_files("../../etc")
        assert "error" in result


# ---------------------------------------------------------------------------
# search_code
# ---------------------------------------------------------------------------

class TestSearchCode:
    def _make_file_mock(self, rel_path: str, content: str) -> MagicMock:
        p = MagicMock(spec=Path)
        p.parts = (_PROJECT_ROOT / rel_path).parts
        p.is_file.return_value = True
        p.relative_to.return_value = Path(rel_path)
        p.read_text.return_value = content
        return p

    def test_finds_matching_lines(self):
        f = self._make_file_mock(
            "backend/main.py",
            "from fastapi import FastAPI\napp = FastAPI()\n"
        )
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.rglob", return_value=iter([f])):
            result = search_code("FastAPI", "backend")
        assert result["total"] == 2
        assert result["matches"][0]["line"] == 1
        assert "FastAPI" in result["matches"][0]["text"]

    def test_case_insensitive(self):
        f = self._make_file_mock("backend/foo.py", "class MyClass:\n    pass\n")
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.rglob", return_value=iter([f])):
            result = search_code("myclass", "backend")
        assert result["total"] == 1

    def test_no_matches_returns_empty(self):
        f = self._make_file_mock("backend/foo.py", "x = 1\n")
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.rglob", return_value=iter([f])):
            result = search_code("zzznomatch", "backend")
        assert result["total"] == 0
        assert result["matches"] == []

    def test_caps_at_50_results(self):
        # File with 60 matching lines
        content = "\n".join(["target_word"] * 60)
        f = self._make_file_mock("backend/big.py", content)
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.rglob", return_value=iter([f])):
            result = search_code("target_word", "backend")
        assert result["total"] == 50
        assert result["truncated"] is True

    def test_missing_directory_returns_error(self):
        with patch("pathlib.Path.exists", return_value=False):
            result = search_code("anything", "nonexistent")
        assert "error" in result


# ---------------------------------------------------------------------------
# read_doc
# ---------------------------------------------------------------------------

class TestReadDoc:
    def test_known_doc_returns_content(self):
        fake_content = "# PRD\nThis is the PRD.\n"
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True), \
             patch("pathlib.Path.read_text", return_value=fake_content):
            result = read_doc("PRD")
        assert result["doc"] == "PRD"
        assert result["content"] == fake_content

    def test_case_insensitive_doc_name(self):
        fake_content = "# DESIGN\n"
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_file", return_value=True), \
             patch("pathlib.Path.read_text", return_value=fake_content):
            result = read_doc("design")
        assert result["doc"] == "DESIGN"

    def test_unknown_doc_returns_error(self):
        result = read_doc("UNKNOWN")
        assert "error" in result
        assert "UNKNOWN" in result["error"]

    def test_all_known_docs_accepted(self):
        fake_content = "content"
        for doc_name in ["PRD", "DESIGN", "SECURITY", "LEARNING", "CLAUDE"]:
            with patch("pathlib.Path.exists", return_value=True), \
                 patch("pathlib.Path.is_file", return_value=True), \
                 patch("pathlib.Path.read_text", return_value=fake_content):
                result = read_doc(doc_name)
            assert "error" not in result, f"{doc_name} should be valid"


# ---------------------------------------------------------------------------
# read_logs
# ---------------------------------------------------------------------------

class TestReadLogs:
    def test_returns_last_n_lines(self):
        log_content = "\n".join(f"line {i}" for i in range(100))
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=log_content):
            result = read_logs(lines=10)
        assert result["lines_read"] == 10
        assert "line 99" in result["content"]
        assert "line 0" not in result["content"]

    def test_no_log_file_returns_note(self):
        with patch("pathlib.Path.exists", return_value=False):
            result = read_logs()
        assert result["content"] == ""
        assert "note" in result
        assert result["lines_read"] == 0

    def test_fewer_lines_than_requested(self):
        log_content = "line 1\nline 2\nline 3"
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=log_content):
            result = read_logs(lines=100)
        assert result["lines_read"] == 3
