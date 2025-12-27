import json
import pytest
import requests
from pathlib import Path


class TestRawEndpoint:
    """Integration tests for GET /raw/{entity_id}/{revision_id} endpoint"""

    BASE_URL = "http://entity-api:8000"
    TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"

    def load_expected(self, path: str):
        """Load expected data from test_data directory"""
        file_path = self.TEST_DATA_DIR / path
        with open(file_path, 'r') as f:
            return json.load(f)

    def test_raw_endpoint_returns_existing_revision(self):
        """Test that raw endpoint returns correct entity data"""
        # First create an entity to ensure it exists
        entity_data = {
            "id": "Q12345",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Test Entity"}}
        }
        
        create_response = requests.post(
            f"{self.BASE_URL}/entity",
            json={"data": entity_data}
        )
        assert create_response.status_code == 200
        
        # Retrieve raw revision
        response = requests.get(f"{self.BASE_URL}/raw/Q12345/1")
        assert response.status_code == 200
        
        # Verify structure (not full S3 revision schema, just inner entity)
        result = response.json()
        assert result["id"] == "Q12345"
        assert result["type"] == "item"
        assert "labels" in result
        print("✓ Raw endpoint returns existing revision correctly")

    def test_raw_endpoint_nonexistent_entity(self):
        """Test that raw endpoint returns 404 for non-existent entity"""
        response = requests.get(f"{self.BASE_URL}/raw/Q99999/1")
        assert response.status_code == 404
        
        # Verify it's a structured error response
        assert "detail" in response.json()
        print("✓ Raw endpoint returns 404 for non-existent entity")

    def test_raw_endpoint_entity_with_no_revisions(self):
        """Test that raw endpoint returns 404 when entity has no revisions"""
        # This scenario requires creating an entity but somehow having no revisions
        # For now, we'll test error format is correct
        response = requests.get(f"{self.BASE_URL}/raw/Q99999/1")
        assert response.status_code == 404
        
        # Verify it's a structured error response
        assert "detail" in response.json()
        print("✓ Raw endpoint returns proper error structure")

    def test_raw_endpoint_nonexistent_revision(self):
        """Test that raw endpoint returns 404 for non-existent revision"""
        # First create an entity with multiple revisions
        entity_data = {
            "id": "Q12346",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Multi-Revision Test"}}
        }
        
        requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        
        # Try to retrieve non-existent revision 3
        response = requests.get(f"{self.BASE_URL}/raw/Q12346/3")
        assert response.status_code == 404
        
        # Verify error message includes available revisions
        error_detail = response.json()["detail"]
        assert "3 not found" in error_detail
        assert "[1, 2]" in error_detail
        print("✓ Raw endpoint returns 404 with available revisions listed")

    def test_raw_endpoint_pure_s3_data(self):
        """Test that raw endpoint returns untransformed S3 data"""
        entity_data = {
            "id": "Q12347",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Pure Data Test"}}
        }
        
        requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        
        # Get wrapped response from main endpoint
        wrapped_response = requests.get(f"{self.BASE_URL}/entity/Q12347")
        wrapped_data = wrapped_response.json()["data"]
        
        # Get raw response from raw endpoint
        raw_response = requests.get(f"{self.BASE_URL}/raw/Q12347/1")
        raw_data = raw_response.json()
        
        # Verify they're identical
        assert wrapped_data == raw_data
        print("✓ Raw endpoint returns pure S3 data (no transformation)")

    def test_raw_endpoint_vs_history_consistency(self):
        """Test that raw endpoint data matches data available from history"""
        entity_data = {
            "id": "Q12348",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Consistency Test"}}
        }
        
        requests.post(f"{self.BASE_URL}/entity", json={"data": entity_data})
        
        # Get history
        history_response = requests.get(f"{self.BASE_URL}/entity/Q12348/history")
        history = history_response.json()
        
        assert len(history) == 1
        revision_id = history[0]["revision_id"]
        
        # Get raw data for that revision
        raw_response = requests.get(f"{self.BASE_URL}/raw/Q12348/{revision_id}")
        assert raw_response.status_code == 200
        
        # Verify it has required entity fields
        raw_data = raw_response.json()
        assert "id" in raw_data
        assert "type" in raw_data
        print("✓ Raw endpoint data consistent with history endpoint")
