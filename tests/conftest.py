"""Pytest configuration and fixtures."""
import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)




