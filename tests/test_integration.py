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
        "labels": {"en": {"language": "en", "value": "Test Entity"}},
        "descriptions": {
            "en": {"language": "en", "value": "A test entity for integration testing"}
        },
    }

    response = api_client.post(f"{base_url}/entity", json=entity_data)
    assert response.status_code == 200

    result = response.json()
    assert result["id"] == "Q99999"
    assert result["revision_id"] == 1

    # Hash computation now works with nested data property
    entity_json = json.dumps(result["data"], sort_keys=True)
    computed_hash = rapidhash(entity_json.encode())

    raw_response = api_client.get(f"{base_url}/raw/Q99999/1")
    raw_data = raw_response.json()
    api_hash = raw_data.get("content_hash")

    assert (
        api_hash == computed_hash
    ), f"API hash {api_hash} must match computed hash {computed_hash}"

    logger.info("✓ Entity creation passed with rapidhash verification")


def test_get_entity(api_client: requests.Session, base_url: str) -> None:
    """Test retrieving an entity"""
    logger = logging.getLogger(__name__)

    # First create an entity
    entity_data = {
        "id": "Q99998",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test Entity for Get"}},
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
        "labels": {"en": {"language": "en", "value": "Test Entity for Update"}},
    }
    api_client.post(f"{base_url}/entity", json=entity_data)

    # Update entity
    updated_entity_data = {
        "id": "Q99997",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test Entity - Updated"}},
        "descriptions": {"en": {"language": "en", "value": "Updated description"}},
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

    assert (
        raw1["content_hash"] != raw2["content_hash"]
    ), "Different content should have different hashes"

    # Verify hash format and values
    if rapidhash is not None:
        entity_json_1 = json.dumps(entity_data, sort_keys=True)
        computed_hash_1 = rapidhash(entity_json_1.encode())
        assert (
            raw1["content_hash"] == computed_hash_1
        ), f"First revision hash mismatch: expected {computed_hash_1}, got {raw1['content_hash']}"

        entity_json_2 = json.dumps(updated_entity_data, sort_keys=True)
        computed_hash_2 = rapidhash(entity_json_2.encode())
        assert (
            raw2["content_hash"] == computed_hash_2
        ), f"Second revision hash mismatch: expected {computed_hash_2}, got {raw2['content_hash']}"

    logger.info("✓ Entity update passed with hash verification")


def test_get_entity_history(api_client: requests.Session, base_url: str) -> None:
    """Test retrieving entity history"""
    logger = logging.getLogger(__name__)

    # Create entity with two revisions
    entity_id = "Q99996"
    entity_data = {
        "id": entity_id,
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test Entity"}},
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
        "labels": {"en": {"language": "en", "value": "Test Entity"}},
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


def test_raw_endpoint_existing_revision(
    api_client: requests.Session, base_url: str
) -> None:
    """Test that raw endpoint returns existing revision"""
    logger = logging.getLogger(__name__)

    # Create entity
    entity_data = {
        "id": "Q55555",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Raw Test Entity"}},
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


def test_idempotent_duplicate_submission(
    api_client: requests.Session, base_url: str
) -> None:
    """Test that identical POST requests return same revision (idempotency)"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q99996",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Idempotent Test"}},
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
    assert (
        revision_id_1 == revision_id_2
    ), "Identical POST should return same revision ID"
    assert result1 == result2, "Responses should be identical"

    # Verify content_hash field and hash computation
    if rapidhash is not None:
        entity_json = json.dumps(entity_data, sort_keys=True)
        computed_hash = rapidhash(entity_json.encode())

        # Get hash from API
        raw_response = api_client.get(f"{base_url}/raw/Q99996/{revision_id_1}").json()
        api_hash = raw_response.get("content_hash")

        # Verify API returned correct hash
        assert (
            api_hash == computed_hash
        ), f"API hash {api_hash} must match computed hash {computed_hash}"

        logger.info(
            f"✓ Idempotent deduplication: same revision {revision_id_1} returned with rapidhash verification"
        )
    else:
        logger.info(
            f"✓ Idempotent deduplication: same revision {revision_id_1} returned (rapidhash not available)"
        )


def test_mass_edit_classification(api_client: requests.Session, base_url: str) -> None:
    """Test mass edit and edit_type classification"""
    logger = logging.getLogger(__name__)

    # Create mass edit with classification
    entity_data = {
        "id": "Q99994",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Mass Edit Test"}},
    }

    response = api_client.post(
        f"{base_url}/entity",
        json={
            "id": entity_data["id"],
            "type": entity_data["type"],
            "labels": entity_data["labels"],
            "is_mass_edit": True,
            "edit_type": "bot-import",
        },
    )
    assert response.status_code == 200

    result = response.json()
    assert result["id"] == "Q99994"
    assert result["revision_id"] == 1

    # Verify fields in S3
    raw_response = api_client.get(f"{base_url}/raw/Q99994/1")
    raw_data = raw_response.json()
    assert raw_data.get("is_mass_edit") == True
    assert raw_data.get("edit_type") == "bot-import"

    # Create manual edit (default behavior)
    manual_data = {
        "id": "Q99993",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Manual Test"}},
    }

    response2 = api_client.post(
        f"{base_url}/entity",
        json={
            "id": manual_data["id"],
            "type": manual_data["type"],
            "labels": manual_data["labels"],
        },
    )
    assert response2.status_code == 200

    # Verify defaults in S3
    raw_response2 = api_client.get(f"{base_url}/raw/Q99993/1")
    raw_data2 = raw_response2.json()
    assert raw_data2.get("is_mass_edit") == False
    assert raw_data2.get("edit_type") == ""

    logger.info("✓ Mass edit classification works correctly")


def test_semi_protection_blocks_not_autoconfirmed_users(
    api_client: requests.Session, base_url: str
) -> None:
    """Semi-protected items should block not-autoconfirmed users"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90001",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    # Create semi-protected item
    api_client.post(
        f"{base_url}/entity", json={**entity_data, "is_semi_protected": True}
    )

    # Attempt edit by not-autoconfirmed user (should fail)
    response = api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "labels": {"en": {"language": "en", "value": "Updated"}},
            "is_not_autoconfirmed_user": True,
        },
    )
    assert response.status_code == 403
    assert "unconfirmed" in response.json()["detail"].lower()

    # Autoconfirmed user should be able to edit
    response = api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "labels": {"en": {"language": "en", "value": "Updated"}},
            "is_not_autoconfirmed_user": False,
        },
    )
    assert response.status_code == 200

    logger.info("✓ Semi-protection blocks not-autoconfirmed users")


def test_semi_protection_allows_autoconfirmed_users(
    api_client: requests.Session, base_url: str
) -> None:
    """Semi-protected items should allow autoconfirmed users to edit"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90001b",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    # Create semi-protected item
    api_client.post(
        f"{base_url}/entity", json={**entity_data, "is_semi_protected": True}
    )

    # Autoconfirmed user edit should succeed
    response = api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "labels": {"en": {"language": "en", "value": "Updated"}},
            "is_not_autoconfirmed_user": False,
        },
    )
    assert response.status_code == 200

    logger.info("✓ Semi-protection allows autoconfirmed users")


def test_locked_items_block_all_edits(
    api_client: requests.Session, base_url: str
) -> None:
    """Locked items should reject all edits"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90002",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    # Create locked item
    api_client.post(f"{base_url}/entity", json={**entity_data, "is_locked": True})

    # Attempt manual edit (should fail)
    response = api_client.post(
        f"{base_url}/entity",
        json={**entity_data, "labels": {"en": {"language": "en", "value": "Updated"}}},
    )
    assert response.status_code == 403
    assert "locked" in response.json()["detail"].lower()

    logger.info("✓ Locked items block all edits")


def test_archived_items_block_all_edits(
    api_client: requests.Session, base_url: str
) -> None:
    """Archived items should reject all edits with distinct error"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90003",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    # Create archived item
    api_client.post(f"{base_url}/entity", json={**entity_data, "is_archived": True})

    # Attempt edit (should fail)
    response = api_client.post(
        f"{base_url}/entity",
        json={**entity_data, "labels": {"en": {"language": "en", "value": "Updated"}}},
    )
    assert response.status_code == 403
    assert "archived" in response.json()["detail"].lower()

    logger.info("✓ Archived items block all edits")


def test_status_flags_stored_in_s3(api_client: requests.Session, base_url: str) -> None:
    """All status flags should be stored in S3"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90004",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "is_semi_protected": True,
            "is_locked": False,
            "is_archived": False,
            "is_dangling": True,
            "is_mass_edit_protected": False,
        },
    )

    raw = api_client.get(f"{base_url}/raw/Q90004/1").json()
    assert raw["is_semi_protected"] == True
    assert raw["is_locked"] == False
    assert raw["is_archived"] == False
    assert raw["is_dangling"] == True
    assert raw["is_mass_edit_protected"] == False

    logger.info("✓ Status flags stored in S3")


def test_status_flags_returned_in_response(
    api_client: requests.Session, base_url: str
) -> None:
    """Status flags should be returned in API response"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90005",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "is_semi_protected": True,
            "is_locked": False,
            "is_archived": False,
            "is_dangling": False,
            "is_mass_edit_protected": True,
        },
    )

    response = api_client.get(f"{base_url}/entity/Q90005")
    data = response.json()
    assert data["is_semi_protected"] == True
    assert data["is_locked"] == False
    assert data["is_archived"] == False
    assert data["is_dangling"] == False
    assert data["is_mass_edit_protected"] == True

    logger.info("✓ Status flags returned in API response")


def test_dangling_flag_set_by_frontend(
    api_client: requests.Session, base_url: str
) -> None:
    """is_dangling should be set by frontend, not computed by backend"""
    logger = logging.getLogger(__name__)

    # Entity without P6104 (frontend sets is_dangling=True)
    entity_no_wp = {"id": "Q90006", "type": "item", "claims": {}}
    api_client.post(f"{base_url}/entity", json={**entity_no_wp, "is_dangling": True})
    raw = api_client.get(f"{base_url}/raw/Q90006/1").json()
    assert raw["is_dangling"] == True

    # Entity with P6104 (frontend sets is_dangling=False)
    entity_with_wp = {"id": "Q90007", "type": "item", "claims": {"P6104": []}}
    api_client.post(f"{base_url}/entity", json={**entity_with_wp, "is_dangling": False})
    raw = api_client.get(f"{base_url}/raw/Q90007/1").json()
    assert raw["is_dangling"] == False

    logger.info("✓ is_dangling flag set by frontend")


def test_query_locked_entities(api_client: requests.Session, base_url: str) -> None:
    """Query should return locked items"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90010",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Locked"}},
    }
    api_client.post(f"{base_url}/entity", json={**entity_data, "is_locked": True})

    response = api_client.get(f"{base_url}/entities?status=locked")
    assert response.status_code == 200
    entities = response.json()
    assert any(e["entity_id"] == "Q90010" for e in entities)

    logger.info("✓ Query locked entities works")


def test_query_semi_protected_entities(
    api_client: requests.Session, base_url: str
) -> None:
    """Query should return semi-protected items"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90011",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Protected"}},
    }
    api_client.post(
        f"{base_url}/entity", json={**entity_data, "is_semi_protected": True}
    )

    response = api_client.get(f"{base_url}/entities?status=semi_protected")
    assert response.status_code == 200
    entities = response.json()
    assert any(e["entity_id"] == "Q90011" for e in entities)

    logger.info("✓ Query semi-protected entities works")


def test_query_archived_entities(api_client: requests.Session, base_url: str) -> None:
    """Query should return archived items"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90012",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Archived"}},
    }
    api_client.post(f"{base_url}/entity", json={**entity_data, "is_archived": True})

    response = api_client.get(f"{base_url}/entities?status=archived")
    assert response.status_code == 200
    entities = response.json()
    assert any(e["entity_id"] == "Q90012" for e in entities)

    logger.info("✓ Query archived entities works")


def test_query_dangling_entities(api_client: requests.Session, base_url: str) -> None:
    """Query should return dangling items"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90013",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Dangling"}},
    }
    api_client.post(f"{base_url}/entity", json={**entity_data, "is_dangling": True})

    response = api_client.get(f"{base_url}/entities?status=dangling")
    assert response.status_code == 200
    entities = response.json()
    assert any(e["entity_id"] == "Q90013" for e in entities)

    logger.info("✓ Query dangling entities works")


def test_query_by_edit_type(api_client: requests.Session, base_url: str) -> None:
    """Query should return entities filtered by edit_type"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90014",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    api_client.post(
        f"{base_url}/entity",
        json={**entity_data, "is_locked": True, "edit_type": "lock-added"},
    )

    response = api_client.get(f"{base_url}/entities?edit_type=lock-added")
    assert response.status_code == 200
    entities = response.json()
    assert any(e["entity_id"] == "Q90014" for e in entities)

    logger.info("✓ Query by edit_type works")


def test_mass_edit_protection_blocks_mass_edits(
    api_client: requests.Session, base_url: str
) -> None:
    """Mass-edit protected items should block mass edits"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90015",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    # Create mass-edit protected item
    api_client.post(
        f"{base_url}/entity", json={**entity_data, "is_mass_edit_protected": True}
    )

    # Attempt mass edit (should fail)
    response = api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "is_mass_edit": True,
            "labels": {"en": {"language": "en", "value": "Updated"}},
        },
    )
    assert response.status_code == 403
    assert "mass edits blocked" in response.json()["detail"].lower()

    # Manual edit should work
    response = api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "is_mass_edit": False,
            "labels": {"en": {"language": "en", "value": "Updated manually"}},
        },
    )
    assert response.status_code == 200

    logger.info("✓ Mass-edit protection works correctly")


def test_mass_protection_edit_types(
    api_client: requests.Session, base_url: str
) -> None:
    """Mass-protection edit types should work"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q90016",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Test"}},
    }

    # Add mass protection
    api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "is_mass_edit_protected": True,
            "edit_type": "mass-protection-added",
        },
    )
    raw = api_client.get(f"{base_url}/raw/Q90016/1").json()
    assert raw["edit_type"] == "mass-protection-added"
    assert raw["is_mass_edit_protected"] == True

    # Remove mass protection
    api_client.post(
        f"{base_url}/entity",
        json={
            **entity_data,
            "is_mass_edit_protected": False,
            "edit_type": "mass-protection-removed",
        },
    )
    raw = api_client.get(f"{base_url}/raw/Q90016/2").json()
    assert raw["edit_type"] == "mass-protection-removed"
    assert raw["is_mass_edit_protected"] == False

    logger.info("✓ Mass-protection edit types work")


def test_soft_delete_entity(api_client: requests.Session, base_url: str) -> None:
    """Test soft deleting an entity"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q99001",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "To Delete"}},
    }

    # Create entity
    api_client.post(f"{base_url}/entity", json=entity_data)

    # Soft delete
    delete_response = api_client.delete(
        f"{base_url}/entity/Q99001",
        json={"delete_type": "soft"},
    )
    assert delete_response.status_code == 200

    result = delete_response.json()
    assert result["id"] == "Q99001"
    assert result["is_deleted"] is True
    assert result["delete_type"] == "soft"
    assert "revision_id" in result

    # Verify entity still accessible (soft delete doesn't hide)
    get_response = api_client.get(f"{base_url}/entity/Q99001")
    assert get_response.status_code == 200

    # Verify deletion revision in S3
    revision_response = api_client.get(f"{base_url}/raw/Q99001/2")
    raw_data = revision_response.json()
    assert raw_data["is_deleted"] is True
    assert raw_data["edit_type"] == "soft-delete"
    assert "entity" in raw_data  # Entity data preserved

    logger.info("✓ Soft delete works correctly")


def test_hard_delete_entity(api_client: requests.Session, base_url: str) -> None:
    """Test hard deleting an entity"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q99002",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "To Hard Delete"}},
    }

    # Create entity
    api_client.post(f"{base_url}/entity", json=entity_data)

    # Hard delete
    delete_response = api_client.delete(
        f"{base_url}/entity/Q99002",
        json={"delete_type": "hard"},
    )
    assert delete_response.status_code == 200

    result = delete_response.json()
    assert result["id"] == "Q99002"
    assert result["is_deleted"] is True
    assert result["delete_type"] == "hard"

    # Verify entity no longer accessible (hard delete hides)
    get_response = api_client.get(f"{base_url}/entity/Q99002")
    assert get_response.status_code == 410  # Gone
    assert "deleted" in get_response.json()["detail"].lower()

    logger.info("✓ Hard delete hides entity correctly")


def test_undelete_entity(api_client: requests.Session, base_url: str) -> None:
    """Test undeleting an entity by creating new revision"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q99003",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "Original"}},
    }

    # Create entity
    api_client.post(f"{base_url}/entity", json=entity_data)

    # Soft delete
    api_client.delete(
        f"{base_url}/entity/Q99003",
        json={
            "delete_type": "soft",
        },
    )

    # Undelete by creating new revision
    undelete_response = api_client.post(
        f"{base_url}/entity",
        json={
            "id": "Q99003",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Undeleted"}},
        },
    )
    assert undelete_response.status_code == 200

    result = undelete_response.json()
    assert result["revision_id"] == 3  # Original (1) + Delete (2) + Undelete (3)

    # Verify entity accessible again
    get_response = api_client.get(f"{base_url}/entity/Q99003")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["labels"]["en"]["value"] == "Undeleted"

    # Verify latest revision not deleted
    raw_response = api_client.get(f"{base_url}/raw/Q99003/3")
    assert raw_response.json()["is_deleted"] is False

    logger.info("✓ Undelete via new revision works")


def test_hard_delete_prevents_undelete(
    api_client: requests.Session, base_url: str
) -> None:
    """Test that hard deleted entities cannot be undeleted"""
    logger = logging.getLogger(__name__)

    entity_data = {
        "id": "Q99004",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "To Hard Delete"}},
    }

    # Create entity
    api_client.post(f"{base_url}/entity", json=entity_data)

    # Hard delete
    api_client.delete(
        f"{base_url}/entity/Q99004",
        json={"delete_type": "hard"},
    )

    # Try to undelete (should fail with 410)
    response = api_client.post(
        f"{base_url}/entity",
        json={
            "id": "Q99004",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Undeleted"}},
        },
    )
    assert response.status_code == 410

    logger.info("✓ Hard delete prevents undelete")

