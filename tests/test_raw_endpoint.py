import json
import logging
import os
from pathlib import Path

import requests


def test_raw_endpoint_returns_existing_revision(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint returns correct entity data"""
    logger = logging.getLogger(__name__)
    
    # Create entity
    entity_data = {
        "id": "Q12345",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test Entity"}}
    }
    
    create_response = api_client.post(
        f"{base_url}/entity",
        json={"data": entity_data}
    )
    assert create_response.status_code == 200
    
    # Retrieve raw revision
    response = api_client.get(f"{base_url}/raw/Q12345/1")
    assert response.status_code == 200
    
    # Verify structure (not full S3 revision schema, just inner entity)
    result = response.json()
    assert result["id"] == "Q12345"
    assert result["type"] == "item"
    assert "labels" in result
    logger.info("✓ Raw endpoint returns existing revision correctly")


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
    
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
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
    
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
    # Get wrapped response from main endpoint
    wrapped_response = api_client.get(f"{base_url}/entity/{entity_id}")
    wrapped_data = wrapped_response.json()["data"]
    
    # Get raw response from raw endpoint
    raw_response = api_client.get(f"{base_url}/raw/{entity_id}/1")
    raw_data = raw_response.json()
    
    # Verify they're identical
    assert wrapped_data == raw_data
    logger.info("✓ Raw endpoint returns pure S3 data (no transformation)")


def test_raw_endpoint_vs_history_consistency(api_client: requests.Session, base_url: str) -> None:
    """Test that raw endpoint data matches data available from history"""
    logger = logging.getLogger(__name__)
    
    entity_id = "Q12348"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Consistency Test"}}
    }
    
    api_client.post(f"{base_url}/entity", json={"data": entity_data})
    
    # Get history
    history_response = api_client.get(f"{base_url}/entity/{entity_id}/history")
    history = history_response.json()
    
    assert len(history) == 1
    revision_id = history[0]["revision_id"]
    
    # Get raw data for that revision
    raw_response = api_client.get(f"{base_url}/raw/{entity_id}/{revision_id}")
    assert raw_response.status_code == 200
    
    # Verify it has required entity fields
    raw_data = raw_response.json()
    assert "id" in raw_data
    assert "type" in raw_data
    logger.info("✓ Raw endpoint data consistent with history endpoint")
