"""Reusable pytest fixtures for end-to-end lifecycle tests."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Set test database before any app code runs (avoids Databricks in get_database_url)
os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

# Ensure tagso package is importable when running tests from repo root
_tagso_dir = Path(__file__).resolve().parent.parent
if str(_tagso_dir) not in sys.path:
    sys.path.insert(0, str(_tagso_dir))


def _make_mock_workspace_client():
    """Create a minimal mock WorkspaceClient for tests that avoid Databricks SDK."""
    mock = type("MockWorkspaceClient", (), {})()
    mock.catalogs = type("Mock", (), {"list": lambda: []})()
    mock.schemas = type("Mock", (), {"list": lambda **kw: []})()
    mock.tables = type(
        "Mock",
        (),
        {"list": lambda **kw: [], "get": lambda **kw: type("Mock", (), {"columns": []})()},
    )()
    return mock


# Patch WorkspaceClient before app module loads (module-level create_app runs on import)
_mock_workspace_client = _make_mock_workspace_client()
patch("databricks.sdk.WorkspaceClient", return_value=_mock_workspace_client).start()


@pytest.fixture
def app():
    """Create a Flask app with in-memory SQLite and mocked WorkspaceClient."""
    from app import create_app

    return create_app(
        config_overrides={
            "database_url": "sqlite:///:memory:",
            "workspace_client": _make_mock_workspace_client(),
        }
    )


@pytest.fixture
def client(app):
    """Flask test client for making requests like the UI."""
    app.config["TESTING"] = True
    return app.test_client()
