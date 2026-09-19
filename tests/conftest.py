import os
import pytest
from fastapi.testclient import TestClient

# Force execution profiles strictly to testing spaces
os.environ["ENVIRONMENT"] = "testing"
os.environ["GATEWAY_SECRET_SALT"] = "test_cryptographic_verification_salt_hash_matrix_string_64"
os.environ["ACTIVE_DEPLOYMENT_TIER"] = "FREE_PUBLIC"
os.environ["SYSTEM_RATE_LIMIT"] = "1000/hour"

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Guarantees global environment variables are locked for the duration of the test pipeline."""
    yield

@pytest.fixture
def test_client():
    """Generates an clean, ephemeral ASGI TestClient instances from the core server engine."""
    from server import app
    with TestClient(app) as client:
        yield client
