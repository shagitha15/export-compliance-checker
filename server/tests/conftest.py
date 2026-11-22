"""
Global Test Suite Configuration & Fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from server.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    TestClient fixture for executing API requests in tests.
    """
    with TestClient(app) as test_client:
        yield test_client
