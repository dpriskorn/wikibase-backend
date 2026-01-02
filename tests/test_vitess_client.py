import sys

import pytest

sys.path.insert(0, "src")

from models.infrastructure.vitess_client import VitessClient
from models.vitess_models import VitessConfig


@pytest.fixture
def vitess_client():
    """Create a real VitessClient connected to test database"""
    config = VitessConfig(
        host="vitess",
        port=15307,
        database="page",
        user="root",
        password="",
    )
    client = VitessClient(config)
    yield client
    client.connection = None


def test_insert_revision_idempotent(vitess_client):
    """Test that insert_revision is idempotent - calling twice with same params doesn't error"""
    entity_id = 123456789
    revision_id = 1
    
    vitess_client.insert_revision(
        entity_id=entity_id,
        revision_id=revision_id,
        is_mass_edit=False,
        edit_type="test-edit",
    )
    
    vitess_client.insert_revision(
        entity_id=entity_id,
        revision_id=revision_id,
        is_mass_edit=False,
        edit_type="test-edit",
    )
    
    conn = vitess_client.connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM entity_revisions WHERE entity_id = %s AND revision_id = %s",
        (entity_id, revision_id),
    )
    count = cursor.fetchone()[0]
    cursor.close()
    
    assert count == 1, "Should only have one record, duplicate inserts should be skipped"


def test_insert_revision_different_params(vitess_client):
    """Test that insert_revision creates separate records for different revisions"""
    entity_id = 987654321
    
    vitess_client.insert_revision(
        entity_id=entity_id,
        revision_id=1,
        is_mass_edit=False,
        edit_type="first-edit",
    )
    
    vitess_client.insert_revision(
        entity_id=entity_id,
        revision_id=2,
        is_mass_edit=True,
        edit_type="second-edit",
    )
    
    conn = vitess_client.connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM entity_revisions WHERE entity_id = %s",
        (entity_id,),
    )
    count = cursor.fetchone()[0]
    cursor.close()
    
    assert count == 2, "Should have two separate records for different revisions"
