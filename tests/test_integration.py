import logging

import requests


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
    
    response = api_client.post(f"{base_url}/entity", json={"data": entity_data})
    assert response.status_code == 200
    
    result = response.json()
    assert result["id"] == "Q99999"
    assert result["revision_id"] == 1
    assert result["data"] == entity_data
    logger.info("✓ Entity creation passed")


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
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
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
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
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
    
    response = api_client.post(f"{base_url}/entity", json={"data": updated_entity_data})
    assert response.status_code == 200
    
    result = response.json()
    assert result["id"] == "Q99997"
    assert result["revision_id"] == 2
    assert result["data"]["labels"]["en"]["value"] == "Test Entity - Updated"
    logger.info("✓ Entity update passed")


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
    
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
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
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
    # Create second revision
    entity_data["labels"]["en"]["value"] = "Updated"
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
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
    
    create_response = api_client.post(f"{base_url}/entity", json={"data": entity_data})
    assert create_response.status_code == 200
    
    # Get raw revision
    response = api_client.get(f"{base_url}/raw/Q55555/1")
    assert response.status_code == 200
    result = response.json()
    
    # Log response body if enabled
    import os
    if os.getenv("TEST_LOG_HTTP_REQUESTS") == "true":
        logger.debug(f"  ← ✓ 200 OK")
        if response.text:
            text_preview = response.text[:200]
            logger.debug(f"    Body: {text_preview}...")
    
    assert result["id"] == "Q55555"
    assert "type" in result
    logger.info("✓ Raw endpoint returns existing revision")


def test_raw_endpoint_nonexistent_entity(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns 404 for non-existent entity"""
    logger = logging.getLogger(__name__)
    response = api_client.get(f"{base_url}/raw/Q77777/1")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    logger.info("✓ Raw endpoint returns 404 for non-existent entity")


def test_raw_endpoint_nonexistent_revision(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns 404 for non-existent revision"""
    logger = logging.getLogger(__name__)
    
    # Create entity
    entity_id = "Q66666"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test Entity"}}
    }
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
    # Try to get non-existent revision
    response = api_client.get(f"{base_url}/raw/{entity_id}/99")
    assert response.status_code == 404
    error_detail = response.json()["detail"]
    assert "99 not found" in error_detail
    logger.info("✓ Raw endpoint returns 404 for non-existent revision")
