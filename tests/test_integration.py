import json
import logging

import requests

from rapidhash import rapidhash


def test_health_check(api_client: requests.Session, base_url: str) -> None:
    """Test that health check endpoint returns OK"""
    logger = logging.getLogger(__name__)
    response = api_client.get(f"{base_url}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["s3"] == "connected"
    assert data["vitess"] == "connected"
    logger.info("✓ Health check passed")


def test_create_entity(api_client: requests.Session, base_url: str) -> None:
    """Test creating a new entity"""
    logger = logging.getLogger(__name__)
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
    
    response = api_client.post(f"{base_url}/entity", json=entity_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["id"] == "Q99999"
    assert result["revision_id"] == 1
    assert result["data"] == entity_data
    
    entity_json = json.dumps(entity_data, sort_keys=True)
    computed_hash = rapidhash(entity_json.encode())
    
    raw_response = api_client.get(f"{base_url}/raw/Q99999/1")
    raw_data = raw_response.json()
    api_hash = raw_data.get("content_hash")
    
    assert api_hash == computed_hash, \
        f"API hash {api_hash} must match computed hash {computed_hash}"
    
    logger.info("✓ Entity creation passed with rapidhash verification")


def test_get_entity(api_client: requests.Session, base_url: str) -> None:
    """Test retrieving an entity"""
    logger = logging.getLogger(__name__)
    
    # First create an entity
    entity_data = {
        "id": "Q99998",
        "type": "item",
        "labels": {
            "en": {"language": "en", "value": "Test Entity for Get"}
        }
    }
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Then retrieve it
    response = api_client.get(f"{base_url}/entity/Q99998")
    assert response.status_code == 200
    
    result = response.json()
    assert result["id"] == "Q99998"
    assert result["revision_id"] == 1
    assert "data" in result
    logger.info("✓ Entity retrieval passed")


def test_update_entity(api_client: requests.Session, base_url: str) -> None:
    """Test updating an entity (create new revision)"""
    logger = logging.getLogger(__name__)
    
    # Create initial entity
    entity_data = {
        "id": "Q99997",
        "type": "item",
        "labels": {
            "en": {"language": "en", "value": "Test Entity for Update"}
        }
    }
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Update entity
    updated_entity_data = {
        "id": "Q99997",
        "type": "item",
        "labels": {
            "en": {"language": "en", "value": "Test Entity - Updated"}
        },
        "descriptions": {
            "en": {"language": "en", "value": "Updated description"}
        }
    }
    
    response = api_client.post(f"{base_url}/entity", json=updated_entity_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["id"] == "Q99997"
    assert result["revision_id"] == 2
    assert result["data"]["labels"]["en"]["value"] == "Test Entity - Updated"
    
    # Verify different content created new revision with different hash
    raw1 = api_client.get(f"{base_url}/raw/Q99997/1").json()
    raw2 = api_client.get(f"{base_url}/raw/Q99997/2").json()
    
    assert raw1["content_hash"] != raw2["content_hash"], \
        "Different content should have different hashes"
    
    # Verify hash format and values
    if rapidhash is not None:
        entity_json_1 = json.dumps(entity_data, sort_keys=True)
        computed_hash_1 = rapidhash(entity_json_1.encode())
        assert raw1["content_hash"] == computed_hash_1, \
            f"First revision hash mismatch: expected {computed_hash_1}, got {raw1['content_hash']}"
        
        entity_json_2 = json.dumps(updated_entity_data, sort_keys=True)
        computed_hash_2 = rapidhash(entity_json_2.encode())
        assert raw2["content_hash"] == computed_hash_2, \
            f"Second revision hash mismatch: expected {computed_hash_2}, got {raw2['content_hash']}"
    
    logger.info("✓ Entity update passed with hash verification")


def test_get_entity_history(api_client: requests.Session, base_url: str) -> None:
    """Test retrieving entity history"""
    logger = logging.getLogger(__name__)
    
    # Create entity with two revisions
    entity_id = "Q99996"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test Entity"}}
    }
    
    api_client.post(f"{base_url}/entity", json=entity_data)
    entity_data["labels"]["en"]["value"] = "Updated Test Entity"
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Get history
    response = api_client.get(f"{base_url}/entity/{entity_id}/history")
    assert response.status_code == 200
    
    history = response.json()
    assert len(history) == 2
    assert history[0]["revision_id"] == 1
    assert history[1]["revision_id"] == 2
    assert "created_at" in history[0]
    assert "created_at" in history[1]
    logger.info("✓ Entity history retrieval passed")


def test_get_specific_revision(api_client: requests.Session, base_url: str) -> None:
    """Test retrieving a specific revision"""
    logger = logging.getLogger(__name__)
    
    # Create entity
    entity_id = "Q99995"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {
            "en": {"language": "en", "value": "Test Entity"}
        }
    }
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Create second revision
    entity_data["labels"]["en"]["value"] = "Updated"
    api_client.post(f"{base_url}/entity", json=entity_data)
    
    # Get first revision
    response = api_client.get(f"{base_url}/entity/{entity_id}/revision/1")
    assert response.status_code == 200
    
    result = response.json()
    assert result["id"] == entity_id
    assert result["labels"]["en"]["value"] == "Test Entity"
    logger.info("✓ Specific revision retrieval passed")


def test_entity_not_found(api_client: requests.Session, base_url: str) -> None:
    """Test that non-existent entities return 404"""
    logger = logging.getLogger(__name__)
    response = api_client.get(f"{base_url}/entity/Q88888")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    logger.info("✓ 404 handling passed")


def test_raw_endpoint_existing_revision(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns existing revision"""
    logger = logging.getLogger(__name__)
    
    # Create entity
    entity_data = {
        "id": "Q55555",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Raw Test Entity"}}
    }
    
    create_response = api_client.post(f"{base_url}/entity", json=entity_data)
    assert create_response.status_code == 200
    
    # Get raw revision
    response = api_client.get(f"{base_url}/raw/Q55555/1")
    assert response.status_code == 200
    result = response.json()
    
    # Check full revision schema
    assert result["schema_version"] == "1.0.0"
    assert result["revision_id"] == 1
    assert "created_at" in result
    assert result["created_by"] == "entity-api"
    assert result["entity_type"] == "item"
    assert result["entity"]["id"] == "Q55555"
    assert result["entity"]["type"] == "item"
    assert "labels" in result["entity"]
    
    # Verify content_hash field
    assert "content_hash" in result, "content_hash field must be present"
    assert isinstance(result["content_hash"], int), "content_hash must be integer"
    
    # Log response body if enabled
    import os
    if os.getenv("TEST_LOG_HTTP_REQUESTS") == "true":
        logger.debug(f"  ← ✓ 200 OK")
        if response.text:
            text_preview = response.text[:200]
            logger.debug(f"    Body: {text_preview}...")
    
    logger.info("✓ Raw endpoint returns full revision schema with content_hash")


def test_idempotent_duplicate_submission(api_client: requests.Session, base_url: str) -> None:
    """Test that identical POST requests return same revision (idempotency)"""
    logger = logging.getLogger(__name__)
    
    entity_data = {
        "id": "Q99996",
        "type": "item",
        "labels": {
            "en": {"language": "en", "value": "Idempotent Test"}
        }
    }
    
    # First POST creates revision 1
    response1 = api_client.post(f"{base_url}/entity", json=entity_data)
    assert response1.status_code == 200
    result1 = response1.json()
    revision_id_1 = result1["revision_id"]
    
    # Second identical POST should return same revision (no new revision)
    response2 = api_client.post(f"{base_url}/entity", json=entity_data)
    assert response2.status_code == 200
    result2 = response2.json()
    revision_id_2 = result2["revision_id"]
    
    # Verify idempotency
    assert revision_id_1 == revision_id_2, \
        "Identical POST should return same revision ID"
    assert result1 == result2, \
        "Responses should be identical"
    
    # Verify content_hash field and hash computation
    if rapidhash is not None:
        entity_json = json.dumps(entity_data, sort_keys=True)
        computed_hash = rapidhash(entity_json.encode())
        
        # Get hash from API
        raw_response = api_client.get(f"{base_url}/raw/Q99996/{revision_id_1}").json()
        api_hash = raw_response.get("content_hash")
        
        # Verify API returned correct hash
        assert api_hash == computed_hash, \
            f"API hash {api_hash} must match computed hash {computed_hash}"
        
        logger.info(f"✓ Idempotent deduplication: same revision {revision_id_1} returned with rapidhash verification")
    else:
        logger.info(f"✓ Idempotent deduplication: same revision {revision_id_1} returned (rapidhash not available)")

