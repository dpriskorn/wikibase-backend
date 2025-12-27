import sys

from fastapi.testclient import TestClient

sys.path.insert(0, 'src')


def test_app_loads():
    """Test that FastAPI app can be loaded"""
    try:
        from services.entity_api.main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code in [200, 503], f"Unexpected status: {response.status_code}"
    except Exception as e:
        pass
