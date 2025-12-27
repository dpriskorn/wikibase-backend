import logging
import sys
import time
import traceback

import requests


def setup_logging():
    """Configure logging based on environment variable"""
    log_level_str = "INFO"  # Default to INFO if settings not available
    log_level = logging.DEBUG if log_level_str == 'DEBUG' else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stdout
    )


class TestLiveIntegration:
    """Live integration tests for the entity API"""

    BASE_URL = "http://entity-api:8000"
    MAX_RETRIES = 30
    RETRY_DELAY = 1
    
    def log_start(self, test_name):
        """Log test start"""
        logging.info(f"→ Starting: {test_name}")
    
    def log_request(self, method, url, body=None):
        """Log HTTP request"""
        if "DEBUG" in sys.argv:
            if body:
                body_preview = str(body)[:200]
                logging.debug(f"  → {method} {url}")
                logging.debug(f"    Body: {body_preview}...")
            else:
                logging.debug(f"  → {method} {url}")
    
    def log_response(self, response, preview=False):
        """Log HTTP response"""
        if "DEBUG" in sys.argv:
            status_color = "green" if response.status_code < 300 else "red"
            logging.debug(f"  ← {response.status_code} {response.reason}")
            if preview and response.text:
                text_preview = response.text[:200]
                logging.debug(f"    Body: {text_preview}...")
    
    def log_success(self, test_name, details=None):
        """Log test success"""
        logging.info(f"✓ {test_name}")
        if details and "DEBUG" in sys.argv:
            logging.debug(f"  Details: {details}")
    
    def log_failure(self, test_name, error):
        """Log test failure with traceback"""
        logging.error(f"✗ {test_name} failed: {error}")
        
        if "DEBUG" in sys.argv:
            import traceback
            logging.error("  Traceback:")
            for line in traceback.format_exc().split('\n'):
                logging.error(f"    {line}")

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
        self.log_start("Health Check")
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["s3"] == "connected"
        assert data["vitess"] == "connected"
        self.log_success("Health Check passed")

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
        
        self.log_request('POST', f"{self.BASE_URL}/entity", json={"data": entity_data})
        response = requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        self.log_response(response)
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["revision_id"] == 1
        assert result["data"] == entity_data
        self.log_success("Entity Creation")
        return result

    def test_get_entity(self):
        """Test retrieving an entity"""
        self.log_start("Entity Retrieval")
        response = requests.get(f"{self.BASE_URL}/entity/Q99999")
        self.log_response(response)
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["revision_id"] == 1
        assert "data" in result
        self.log_success("Entity Retrieval")
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
        
        self.log_request('POST', f"{self.BASE_URL}/entity", json={"data": entity_data})
        response = requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        self.log_response(response)
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["revision_id"] == 2
        assert result["data"]["labels"]["en"]["value"] == "Test Entity - Updated"
        self.log_success("Entity Update")
        return result
    
    def test_get_entity_history(self):
        """Test retrieving entity history"""
        self.log_start("Entity History Retrieval")
        response = requests.get(f"{self.BASE_URL}/entity/Q99999/history")
        self.log_response(response)
        
        history = response.json()
        assert len(history) == 2
        assert history[0]["revision_id"] == 1
        assert history[1]["revision_id"] == 2
        assert "created_at" in history[0]
        assert "created_at" in history[1]
        self.log_success("Entity History Retrieval")
        return history
    
    def test_get_specific_revision(self):
        """Test retrieving a specific revision"""
        self.log_start("Specific Revision Retrieval")
        response = requests.get(f"{self.BASE_URL}/entity/Q99999/revision/1")
        self.log_response(response)
        
        result = response.json()
        assert result["id"] == "Q99999"
        assert result["labels"]["en"]["value"] == "Test Entity"
        self.log_success("Specific Revision Retrieval")
    
    def test_entity_not_found(self):
        """Test that non-existent entities return 404"""
        self.log_start("404 Handling (non-existent entity)")
        response = requests.get(f"{self.BASE_URL}/entity/Q99998")
        self.log_response(response)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        self.log_success("404 Handling")
    
    def test_raw_endpoint_existing_revision(self):
        """Test that raw endpoint returns existing revision"""
        entity_data = {
            "id": "Q55555",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Raw Test Entity"}}
        }
        
        self.log_request('POST', f"{self.BASE_URL}/entity", json={"data": entity_data})
        create_response = requests.post(
            f"{self.BASE_URL}/entity",
            json={"data": entity_data}
        )
        assert create_response.status_code == 200
        self.log_response(create_response)
        
        self.log_start("Raw Endpoint (existing revision)")
        response = requests.get(f"{self.BASE_URL}/raw/Q55555/1")
        self.log_response(response)
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == "Q55555"
        assert "type" in result
        self.log_success("Raw Endpoint (existing revision)", f"Entity Q55555, revision 1")
    
    def test_raw_endpoint_nonexistent_entity(self):
        """Test that raw endpoint returns 404 for non-existent entity"""
        self.log_start("Raw Endpoint (non-existent entity)")
        response = requests.get(f"{self.BASE_URL}/raw/Q88888/1")
        self.log_response(response)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        self.log_success("Raw Endpoint (non-existent entity)")
    
    def test_raw_endpoint_nonexistent_revision(self):
        """Test that raw endpoint returns 404 for non-existent revision"""
        self.log_start("Raw Endpoint (non-existent revision)")
        response = requests.get(f"{self.BASE_URL}/raw/Q99999/99")
        self.log_response(response)
        assert response.status_code == 404
        error_detail = response.json()["detail"]
        assert "99 not found" in error_detail
        self.log_success("Raw Endpoint (non-existent revision)", f"Entity Q99999, revision 99, available: [1, 2]")

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
        test.test_raw_endpoint_existing_revision()
        test.test_raw_endpoint_nonexistent_entity()
        test.test_raw_endpoint_nonexistent_revision()
        
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
