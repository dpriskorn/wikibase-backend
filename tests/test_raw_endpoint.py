import json
import logging

import requests

from rapidhash import rapidhash


def test_raw_endpoint_returns_existing_revision(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns correct entity data with content hash"""
    logger = logging.getLogger(__name__)
    
    # Create entity
    entity_data = {
        "id": "Q55555",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Raw Test Entity"}}
    }
    
    create_response = api_client.post(
        f"{base_url}/entity",
        json=entity_data
    )
    assert create_response.status_code == 200
    
    # Retrieve raw revision
    response = api_client.get(f"{base_url}/raw/Q55555/1")
    assert response.status_code == 200
    
    # Verify full revision schema
    result = response.json()
    assert result["schema_version"] == "1.0.0"
    assert result["revision_id"] == 1
    assert "created_at" in result
    assert result["created_by"] == "entity-api"
    assert result["entity_type"] == "item"
    assert "entity" in result
    assert result["entity"]["id"] == "Q55555"
    assert result["entity"]["type"] == "item"
    assert "labels" in result["entity"]
    
    # Verify content_hash field
    assert "content_hash" in result, "content_hash field must be present"
    assert isinstance(result["content_hash"], int), "content_hash must be integer"
    
    # Verify hash using rapidhash if available
    if rapidhash is not None:
        entity_json = json.dumps(entity_data, sort_keys=True)
        computed_hash = rapidhash(entity_json.encode())
        assert result["content_hash"] == computed_hash, \
            f"API hash must match computed hash"
        
        logger.info("✓ Raw endpoint returns full revision schema with rapidhash verification")
    else:
        logger.info("✓ Raw endpoint returns full revision schema with content_hash")


def test_raw_endpoint_nonexistent_entity(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns 404 for non-existent entity"""
    logger = logging.getLogger(__name__)
    response = api_client.get(f"{base_url}/raw/Q22222/1")
    assert response.status_code == 404
    
    # Verify it's a structured error response
    assert "detail" in response.json()
    logger.info("✓ Raw endpoint returns 404 for non-existent entity")


def test_raw_endpoint_nonexistent_revision(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns 404 for non-existent revision"""
    logger = logging.getLogger(__name__)
    
    # Create entity with multiple revisions
    entity_id = "Q12346"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Multi-Revision Test"}}
    }
    
    api_client.post(f"{base_url}/entity", json=entity_data)
    entity_data["labels"]["en"]["value"] = "Updated Multi-Revision Test"
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Try to retrieve non-existent revision 3
    response = api_client.get(f"{base_url}/raw/{entity_id}/3")
    assert response.status_code == 404
    
    # Verify error message includes available revisions
    error_detail = response.json()["detail"]
    assert "3 not found" in error_detail
    assert "[1, 2]" in error_detail
    logger.info("✓ Raw endpoint returns 404 with available revisions listed")


def test_raw_endpoint_pure_s3_data(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns untransformed S3 data"""
    logger = logging.getLogger(__name__)
    
    entity_id = "Q12347"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Pure Data Test"}}
    }
    
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Get wrapped response from main endpoint
    wrapped_response = api_client.get(f"{base_url}/entity/{entity_id}")
    wrapped_data = wrapped_response.json()["data"]
    
    # Get raw response from raw endpoint
    raw_response = api_client.get(f"{base_url}/raw/{entity_id}/1")
    raw_data = raw_response.json()
    
    # Verify they're identical (compare entity content)
    assert wrapped_data == raw_data["entity"]
    
    # Verify content_hash field
    assert "content_hash" in raw_data
    assert isinstance(raw_data["content_hash"], int)
    
    # Verify hash using rapidhash if available
    if rapidhash is not None:
        entity_json = json.dumps(entity_data, sort_keys=True)
        computed_hash = rapidhash(entity_json.encode())
        assert raw_data["content_hash"] == computed_hash, \
                f"API hash {raw_data['content_hash']} must match computed hash {computed_hash}"
    
        logger.info("✓ Main endpoint entity matches raw endpoint entity with rapidhash verification")
    else:
        logger.info("✓ Main endpoint entity matches raw endpoint entity")


def test_raw_endpoint_vs_history_consistency(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint data matches data available from history"""
    logger = logging.getLogger(__name__)
    
    entity_id = "Q12348"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Consistency Test"}}
    }
    
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Get history
    history_response = api_client.get(f"{base_url}/entity/{entity_id}/history")
    history = history_response.json()
    
    assert len(history) == 1
    revision_id = history[0]["revision_id"]
    
    # Get raw data for that revision
    raw_response = api_client.get(f"{base_url}/raw/{entity_id}/{revision_id}")
    assert raw_response.status_code == 200
    
    # Verify it has required entity fields (nested)
    raw_data = raw_response.json()
    assert "entity" in raw_data
    assert "schema_version" in raw_data
    assert raw_data["entity"]["id"] == entity_id
    assert raw_data["entity"]["type"] == "item"
    
    # Verify content_hash field
    assert "content_hash" in raw_data
    assert isinstance(raw_data["content_hash"], int)
    
    logger.info("✓ Raw endpoint data consistent with history endpoint with content_hash")


def test_raw_endpoint_nonexistent_entity_2(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns 404 for non-existent entity"""
    logger = logging.getLogger(__name__)
    response = api_client.get(f"{base_url}/raw/Q77777/1")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    logger.info("✓ Raw endpoint returns 404 for non-existent entity 2")


def test_raw_endpoint_nonexistent_revision_2(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns 404 for non-existent revision"""
    logger = logging.getLogger(__name__)
    
    # Create entity with multiple revisions
    entity_id = "Q12349"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Multi-Revision Test"}}
    }
    
    api_client.post(f"{base_url}/entity", json=entity_data)
    entity_data["labels"]["en"]["value"] = "Updated Multi-Revision Test 2"
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Try to retrieve non-existent revision 3
    response = api_client.get(f"{base_url}/raw/{entity_id}/3")
    assert response.status_code == 404
    
    # Verify error message includes available revisions
    error_detail = response.json()["detail"]
    assert "3 not found" in error_detail
    assert "[1, 2]" in error_detail
    logger.info("✓ Raw endpoint returns 404 with available revisions listed 2")
