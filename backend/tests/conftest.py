"""
Test configuration — sets minimal env vars so Settings() loads without a real .env file.
All Drive/Sheets calls are mocked in individual test files.
"""

import os
import pytest


def pytest_configure(config):
    """Set required env vars before any module imports run."""
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
    os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
    os.environ.setdefault("GOOGLE_REFRESH_TOKEN", "test-refresh-token")
    os.environ.setdefault("GOOGLE_SHEET_ID", "test-sheet-id")
    os.environ.setdefault("DRIVE_FOLDER_ID", "test-folder-id")
    os.environ.setdefault("DATA_STORE", "sheets")
    os.environ.setdefault("FAMILY_NAME", "Test Family")
