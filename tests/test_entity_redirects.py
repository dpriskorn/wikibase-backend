import pytest

from models.entity import (
    EntityRedirectRequest,
    EntityRedirectResponse,
    EntityResponse,
    RedirectRevertRequest,
    EditType,
)
from fastapi import HTTPException


class MockVitessClient:
    """Mock Vitess client for testing without database"""
    
    def __init__(self):
        self.resolved_ids = {}
        self.redirects = {}
        self.redirects_to = {}
        self.deleted_entities = set()
        self.locked_entities = set()
        self.archived_entities = set()
    
    def resolve_id(self, entity_id: str) -> int | None:
        if entity_id in self.resolved_ids:
            return self.resolved_ids[entity_id]
        return None
    
    def get_incoming_redirects(self, entity_internal_id: int) -> list[str]:
        return self.redirects.get(entity_internal_id, [])
    
    def get_redirect_target(self, entity_internal_id: int) -> str | None:
        return self.redirects_to.get(entity_internal_id, None)
    
    def is_entity_deleted(self, entity_internal_id: int) -> bool:
        return entity_internal_id in self.deleted_entities

    def is_entity_locked(self, entity_internal_id: int) -> bool:
        return entity_internal_id in self.locked_entities

    def is_entity_archived(self, entity_internal_id: int) -> bool:
        return entity_internal_id in self.archived_entities

    def get_head(self, entity_id: int) -> int:
        """Get current head revision for entity (for testing)"""
        return 42
    
    def create_redirect(
        self,
        redirect_from_internal_id: int,
        redirect_from_entity_id: str,
        redirect_to_internal_id: int,
        redirect_to_entity_id: str,
        created_by: str = "entity-api",
    ) -> None:
        self.redirects[redirect_from_internal_id] = redirect_to_internal_id
        self.redirects_to[redirect_from_internal_id] = redirect_to_entity_id
    
    def set_redirect_target(
        self,
        entity_internal_id: int,
        redirects_to_internal_id: int | None,
    ) -> None:
        self.redirects_to[entity_internal_id] = redirects_to_internal_id


class MockS3Client:
    """Mock S3 client for testing without S3"""
    
    def __init__(self):
        self.written_revisions = {}
    
    def read_revision(self, entity_id: str, revision_id: int):
        return self.written_revisions.get(revision_id, {
            "revision_id": revision_id,
            "data": {
                "id": entity_id,
                "type": "item",
                "labels": {},
                "descriptions": {},
                "aliases": {},
                "claims": {},
                "sitelinks": {}
            }
        })
    
    def write_entity_revision(
        self,
        internal_id: int,
        entity_id: str,
        revision_id: int,
        entity_type: str,
        data: dict,
        edit_type: str = "",
        created_by: str = "entity-api",
    ) -> int:
        data["revision_id"] = revision_id
        self.written_revisions[revision_id] = data
        return revision_id

    def read_full_revision(self, entity_id: str, revision_id: int) -> dict:
        """Read S3 object and return parsed full revision JSON (matches real client)"""
        return self.written_revisions.get(revision_id, {
            "schema_version": "1.0.0",
            "revision_id": revision_id,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": "entity-api",
            "is_mass_edit": False,
            "edit_type": "",
            "entity_type": "item",
            "is_semi_protected": False,
            "is_locked": False,
            "is_archived": False,
            "is_dangling": False,
            "is_mass_edit_protected": False,
            "is_deleted": False,
            "is_redirect": False,
            "data": {
                "id": entity_id,
                "type": "item",
                "labels": {},
                "descriptions": {},
                "aliases": {},
                "claims": {},
                "sitelinks": {}
            }
        })


class RedirectService:
    """Mock RedirectService for testing"""
    
    def __init__(self, s3_client, vitess_client):
        self.s3 = s3_client
        self.vitess = vitess_client
    
    def create_redirect(self, request: EntityRedirectRequest):
        vitess = self.vitess
        s3 = self.s3
        
        from_internal_id = vitess.resolve_id(request.redirect_from_id)
        to_internal_id = vitess.resolve_id(request.redirect_to_id)

        if from_internal_id is None:
            raise HTTPException(status_code=404, detail="Source entity not found")
        if to_internal_id is None:
            raise HTTPException(status_code=404, detail="Target entity not found")

        if from_internal_id == to_internal_id:
            raise HTTPException(status_code=400, detail="Cannot redirect to self")

        existing_target = vitess.get_redirect_target(from_internal_id)
        if existing_target is not None:
            raise HTTPException(status_code=409, detail="Redirect already exists")

        if vitess.is_entity_deleted(from_internal_id):
            raise HTTPException(status_code=423, detail="Source entity has been deleted")
        if vitess.is_entity_deleted(to_internal_id):
            raise HTTPException(status_code=423, detail="Target entity has been deleted")

        if vitess.is_entity_locked(to_internal_id) or vitess.is_entity_archived(to_internal_id):
            raise HTTPException(status_code=423, detail="Target entity is locked or archived")

        target_revision = s3.read_full_revision(request.redirect_to_id, vitess.get_head(request.redirect_to_id))
        target_data = target_revision

        redirect_revision_data = {
            "schema_version": "1.1.0",
            "redirects_to": request.redirect_to_id,
            "entity": {
                "id": request.redirect_from_id,
                "type": "item",
                "labels": {},
                "descriptions": {},
                "aliases": {},
                "claims": {},
                "sitelinks": {}
            }
        }

        redirect_revision_id = s3.write_entity_revision(
            internal_id=from_internal_id,
            entity_id=request.redirect_from_id,
            revision_id=1,
            entity_type="item",
            data=redirect_revision_data,
            edit_type=EditType.REDIRECT_CREATE,
            created_by=request.created_by,
        )

        vitess.create_redirect(
            redirect_from_internal_id=from_internal_id,
            redirect_from_entity_id=request.redirect_from_id,
            redirect_to_internal_id=to_internal_id,
            redirect_to_entity_id=request.redirect_to_id,
            created_by=request.created_by,
        )

        vitess.set_redirect_target(
            entity_internal_id=from_internal_id,
            redirects_to_internal_id=to_internal_id,
        )

        from datetime import datetime
        
        return EntityRedirectResponse(
            redirect_from_id=request.redirect_from_id,
            redirect_to_id=request.redirect_to_id,
            redirect_from_internal_id=from_internal_id,
            redirect_to_internal_id=to_internal_id,
            created_at=datetime.utcnow().isoformat(),
            revision_id=redirect_revision_id,
        )

    def revert_redirect(self, entity_id: str, revert_to_revision_id: int):
        vitess = self.vitess
        s3 = self.s3
        
        internal_id = vitess.resolve_id(entity_id)
        current_redirect_target = vitess.get_redirect_target(internal_id)

        if current_redirect_target is None:
            raise HTTPException(status_code=404, detail="Entity is not a redirect")

        if vitess.is_entity_deleted(internal_id):
            raise HTTPException(status_code=423, detail="Entity has been deleted")

        if vitess.is_entity_locked(internal_id) or vitess.is_entity_archived(internal_id):
            raise HTTPException(status_code=423, detail="Entity is locked or archived")

        target_revision = s3.read_full_revision(entity_id, revert_to_revision_id)
        target_data = target_revision
        
        new_revision_data = {
            "schema_version": "1.1.0",
            "redirects_to": None,
            "entity": target_data.get("data", target_data)
        }

        new_revision_id = s3.write_entity_revision(
            internal_id=internal_id,
            entity_id=entity_id,
            revision_id=2,
            entity_type="item",
            data=new_revision_data,
            edit_type=EditType.REDIRECT_REVERT,
            created_by="entity-api",
        )

        vitess.set_redirect_target(
            entity_internal_id=internal_id,
            redirects_to_internal_id=None,
        )

        return EntityResponse(
            id=entity_id,
            revision_id=new_revision_id,
            data=new_revision_data["entity"]
        )


@pytest.fixture
def redirect_service():
    """Fixture providing RedirectService with mock clients"""
    vitess = MockVitessClient()
    s3 = MockS3Client()
    
    # Set up default Q42 entity for tests
    vitess.resolved_ids["Q42"] = 42
    
    return RedirectService(s3, vitess)


def test_create_redirect_success(redirect_service):
    """Test successful redirect creation"""
    vitess = redirect_service.vitess
    
    # Set up both source and target entities
    vitess.resolved_ids["Q100"] = 100
    vitess.resolved_ids["Q42"] = 42
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    response = redirect_service.create_redirect(request)
    
    assert response.redirect_from_id == "Q100"
    assert response.redirect_to_id == "Q42"
    assert response.redirect_from_internal_id == 100
    assert response.redirect_to_internal_id == 42
    assert response.revision_id == 1
    assert response.created_at is not None
    
    assert redirect_service.vitess.get_redirect_target(100) == "Q42"
    assert 100 in redirect_service.vitess.redirects


def test_create_redirect_circular_prevention(redirect_service):
    """Test that redirecting to self is prevented"""
    vitess = redirect_service.vitess
    
    vitess.resolved_ids["Q100"] = 100
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 400
        assert "Cannot redirect to self" in e.detail.lower()


def test_create_redirect_source_not_found(redirect_service):
    """Test that source entity not found raises 404"""
    vitess = redirect_service.vitess
    
    # Don't set Q999 in resolved_ids - source doesn't exist
    
    request = EntityRedirectRequest(
        redirect_from_id="Q999",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        assert "source entity not found" in e.detail.lower()


def test_create_redirect_target_not_found(redirect_service):
    """Test that target entity not found raises 404"""
    vitess = redirect_service.vitess
    
    vitess.resolved_ids["Q100"] = 100
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q999",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        assert "target entity not found" in e.detail.lower()


def test_create_redirect_target_already_redirect(redirect_service):
    """Test that redirecting to an entity that's already a redirect is prevented"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.resolved_ids["Q200"] = 200
    
    vitess.resolved_ids["Q42"] = 42
    vitess.set_redirect_target(200, "Q42")
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 409
        assert "Redirect already exists" in e.detail.lower()


def test_create_redirect_source_deleted(redirect_service):
    """Test that redirecting from a deleted entity is prevented"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.resolved_ids["Q42"] = 42
    vitess.deleted_entities.add(100)
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 423
        assert "deleted" in e.detail.lower()


def test_create_redirect_target_deleted(redirect_service):
    """Test that redirecting to a deleted entity is prevented"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.resolved_ids["Q42"] = 42
    vitess.deleted_entities.add(42)
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 423
        assert "deleted" in e.detail.lower()


def test_create_redirect_source_locked(redirect_service):
    """Test that redirecting from a locked entity is prevented"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.resolved_ids["Q42"] = 42
    vitess.locked_entities.add(100)
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 423
        assert "locked" in e.detail.lower()


def test_create_redirect_source_archived(redirect_service):
    """Test that redirecting to an archived entity is prevented"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.resolved_ids["Q42"] = 42
    vitess.archived_entities.add(42)
    
    request = EntityRedirectRequest(
        redirect_from_id="Q100",
        redirect_to_id="Q42",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.create_redirect(request)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 423
        assert "archived" in e.detail.lower()


def test_revert_redirect_success(redirect_service):
    """Test successful redirect revert"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.set_redirect_target(100, "Q42")
    s3.written_revisions[1] = {
        "revision_id": 1,
        "data": {
            "id": "Q100",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "Original Label"}},
            "descriptions": {"en": {"language": "en", "value": "Original Description"}},
            "claims": {},
            "sitelinks": {}
        }
    }
    
    request = RedirectRevertRequest(
        revert_to_revision_id=1,
        revert_reason="Test revert",
        created_by="test-user"
    )
    
    response = redirect_service.revert_redirect(entity_id="Q100", revert_to_revision_id=request.revert_to_revision_id)
    
    assert response.id == "Q100"
    assert response.revision_id == 2
    assert response.data["id"] == "Q100"
    assert response.data["labels"]["en"]["value"] == "Original Label"
    
    assert vitess.get_redirect_target(100) is None


def test_revert_redirect_entity_not_redirect(redirect_service):
    """Test that reverting a non-redirect entity raises 404"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    
    request = RedirectRevertRequest(
        revert_to_revision_id=1,
        revert_reason="Test revert",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.revert_redirect(entity_id="Q100", revert_to_revision_id=request.revert_to_revision_id)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        assert "not a redirect" in e.detail.lower()


def test_revert_redirect_entity_deleted(redirect_service):
    """Test that reverting a deleted entity raises 423"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.set_redirect_target(100, "Q42")  # Set up as redirect first
    vitess.deleted_entities.add(100)
    
    request = RedirectRevertRequest(
        revert_to_revision_id=1,
        revert_reason="Test revert",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.revert_redirect(entity_id="Q100", revert_to_revision_id=request.revert_to_revision_id)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 423
        assert "deleted" in e.detail.lower()


def test_revert_redirect_entity_locked(redirect_service):
    """Test that reverting a locked entity raises 423"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.set_redirect_target(100, "Q42")  # Set up as redirect first
    vitess.locked_entities.add(100)
    
    request = RedirectRevertRequest(
        revert_to_revision_id=1,
        revert_reason="Test revert",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.revert_redirect(entity_id="Q100", revert_to_revision_id=request.revert_to_revision_id)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 423
        assert "locked" in e.detail.lower()


def test_revert_redirect_entity_archived(redirect_service):
    """Test that reverting an archived entity raises 423"""
    vitess = redirect_service.vitess
    s3 = redirect_service.s3
    
    vitess.resolved_ids["Q100"] = 100
    vitess.set_redirect_target(100, "Q42")  # Set up as redirect first
    vitess.archived_entities.add(100)
    
    request = RedirectRevertRequest(
        revert_to_revision_id=1,
        revert_reason="Test revert",
        created_by="test-user"
    )
    
    from fastapi import HTTPException
    try:
        redirect_service.revert_redirect(entity_id="Q100", revert_to_revision_id=request.revert_to_revision_id)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 423
        assert "archived" in e.detail.lower()
