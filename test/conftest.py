import pytest
import os
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(scope="session", autouse=True)
def mock_env():
    # Only set if not already set, to respect user's choice or previous fixtures
    # But for now, we assume we want to fix the issue where USE_MOCK_DATA=true fails.
    # The failure was due to split brain.
    # We don't force it here because we want to allow USE_MOCK_DATA=false too.
    yield

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
