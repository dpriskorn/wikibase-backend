from datetime import timezone

from fastapi import HTTPException

from models.entity import (
    EditType,
    EntityRedirectRequest,
    EntityRedirectResponse,
    EntityResponse,
)
from models.infrastructure.s3_client import S3Client
from models.infrastructure.vitess_client import VitessClient


class RedirectService:
    """Service for managing entity redirects"""

    def __init__(self, s3_client: S3Client, vitess_client: VitessClient):
        self.s3 = s3_client
        self.vitess = vitess_client

    def create_redirect(
        self,
        request: EntityRedirectRequest,
    ) -> EntityRedirectResponse:
        """Mark an entity as redirect to another entity"""
        from datetime import datetime

        from_internal_id = self.vitess.resolve_id(request.redirect_from_id)
        to_internal_id = self.vitess.resolve_id(request.redirect_to_id)

        if from_internal_id is None:
            raise HTTPException(status_code=404, detail="Source entity not found")
        if to_internal_id is None:
            raise HTTPException(status_code=404, detail="Target entity not found")

        if from_internal_id == to_internal_id:
            raise HTTPException(status_code=400, detail="Cannot redirect to self")

        existing_target = self.vitess.get_redirect_target(to_internal_id)
        if existing_target is not None:
            raise HTTPException(status_code=409, detail="Redirect already exists")

        if self.vitess.is_entity_deleted(from_internal_id):
            raise HTTPException(
                status_code=423, detail="Source entity has been deleted"
            )
        if self.vitess.is_entity_deleted(from_internal_id):
            raise HTTPException(
                status_code=423, detail="Source entity has been deleted"
            )
        if self.vitess.is_entity_deleted(to_internal_id):
            raise HTTPException(
                status_code=423, detail="Target entity has been deleted"
            )

        if self.vitess.is_entity_locked(
            to_internal_id
        ) or self.vitess.is_entity_archived(to_internal_id):
            raise HTTPException(
                status_code=423, detail="Target entity is locked or archived"
            )

        target_revision = self.s3.read_full_revision(
            request.redirect_to_id,
            self.vitess.get_head(to_internal_id),
        )

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
                "sitelinks": {},
            },
        }

        redirect_revision_id = self.s3.write_entity_revision(
            entity_id=request.redirect_from_id,
            entity_type="item",
            data=redirect_revision_data,
            edit_type=EditType.REDIRECT_CREATE,
            created_by=request.created_by,
        )

        self.vitess.create_redirect(
            redirect_from_internal_id=from_internal_id,
            redirect_from_entity_id=request.redirect_from_id,
            redirect_to_internal_id=to_internal_id,
            redirect_to_entity_id=request.redirect_to_id,
            created_by=request.created_by,
        )

        self.vitess.set_redirect_target(
            entity_internal_id=from_internal_id,
            redirects_to_internal_id=to_internal_id,
        )

        return EntityRedirectResponse(
            redirect_from_id=request.redirect_from_id,
            redirect_to_id=request.redirect_to_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            revision_id=redirect_revision_id,
        )

    def revert_redirect(
        self,
        entity_id: str,
        revert_to_revision_id: int,
    ) -> EntityResponse:
        """Revert a redirect entity back to normal using revision-based restore"""

        internal_id = self.vitess.resolve_id(entity_id)
        current_redirect_target = self.vitess.get_redirect_target(internal_id)

        if current_redirect_target is None:
            raise HTTPException(status_code=404, detail="Entity is not a redirect")

        if self.vitess.is_entity_deleted(internal_id):
            raise HTTPException(status_code=423, detail="Entity has been deleted")

        if self.vitess.is_entity_locked(internal_id) or self.vitess.is_entity_archived(
            internal_id
        ):
            raise HTTPException(status_code=423, detail="Entity is locked or archived")

        target_revision = self.s3.read_full_revision(entity_id, revert_to_revision_id)
        target_data = target_revision["data"]

        new_revision_data = {
            "schema_version": "1.1.0",
            "redirects_to": None,
            "entity": target_data["entity"],
        }

        new_revision_id = self.s3.write_entity_revision(
            entity_id=entity_id,
            entity_type="item",
            data=new_revision_data,
            edit_type=EditType.REDIRECT_REVERT,
            created_by="entity-api",
        )

        self.vitess.set_redirect_target(
            entity_internal_id=internal_id,
            redirects_to_internal_id=None,
        )

        return EntityResponse(
            id=entity_id, revision_id=new_revision_id, data=new_revision_data["entity"]
        )
