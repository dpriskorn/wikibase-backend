import requests
import time
from typing import Dict, Any


class TestLiveIntegration:
    """Live integration tests for the entity API"""

    BASE_URL = "http://entity-api:8000"
    MAX_RETRIES = 30
    RETRY_DELAY = 1

    def wait_for_api(self):
        """Wait for the API to become healthy"""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(f"{self.BASE_URL}/health", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "ok":
                        print(f"API healthy after {attempt + 1} attempts")
                        return True
            except requests.RequestException:
                pass
            time.sleep(self.RETRY_DELAY)
        raise AssertionError("API did not become healthy within timeout")

    def test_health_check(self):
        """Test that the health check endpoint returns OK"""
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["s3"] == "connected"
        assert data["vitess"] == "connected"
        print("✓ Health check passed")

    def test_create_entity(self):
        """Test creating a new entity"""
        entity_data = {
            "id": "Q99999",
            "type": "item",
            "labels": {
                "en": {"language": "en", "value": "Test Entity"}
            },
            "descriptions": {
                "en": {"language": "en", "value": "A test entity for integration testing"}
            }
        }
        
        response = requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["revision_id"] == 1
        assert result["data"] == entity_data
        print("✓ Entity creation passed")
        return result

    def test_get_entity(self):
        """Test retrieving an entity"""
        response = requests.get(f"{self.BASE_URL}/entity/Q99999")
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["revision_id"] == 1
        assert "data" in result
        print("✓ Entity retrieval passed")
        return result

    def test_update_entity(self):
        """Test updating an entity (create new revision)"""
        entity_data = {
            "id": "Q99999",
            "type": "item",
            "labels": {
                "en": {"language": "en", "value": "Test Entity - Updated"}
            },
            "descriptions": {
                "en": {"language": "en", "value": "Updated description"}
            }
        }
        
        response = requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["revision_id"] == 2
        assert result["data"]["labels"]["en"]["value"] == "Test Entity - Updated"
        print("✓ Entity update passed")
        return result

    def test_get_entity_history(self):
        """Test retrieving entity history"""
        response = requests.get(f"{self.BASE_URL}/entity/Q99999/history")
        assert response.status_code == 200
        
        history = response.json()
        assert len(history) == 2
        assert history[0]["revision_id"] == 1
        assert history[1]["revision_id"] == 2
        assert "created_at" in history[0]
        assert "created_at" in history[1]
        print("✓ Entity history retrieval passed")
        return history

    def test_get_specific_revision(self):
        """Test retrieving a specific revision"""
        response = requests.get(f"{self.BASE_URL}/entity/Q99999/revision/1")
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["labels"]["en"]["value"] == "Test Entity"
        print("✓ Specific revision retrieval passed")

    def test_entity_not_found(self):
        """Test that non-existent entities return 404"""
        response = requests.get(f"{self.BASE_URL}/entity/Q99998")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        print("✓ 404 handling passed")


def run_tests():
    """Run all integration tests"""
    test = TestLiveIntegration()
    
    print("\n=== Starting Live Integration Tests ===\n")
    
    try:
        test.wait_for_api()
        test.test_health_check()
        test.test_create_entity()
        test.test_get_entity()
        test.test_update_entity()
        test.test_get_entity_history()
        test.test_get_specific_revision()
        test.test_entity_not_found()
        
        print("\n=== All Tests Passed ✓ ===\n")
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test Failed: {e}\n")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}\n")
        return 1


if __name__ == "__main__":
    exit(run_tests())
