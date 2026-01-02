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

        if request.redirect_from_id == request.redirect_to_id:
            raise HTTPException(status_code=400, detail="Cannot redirect to self")

        existing_target = self.vitess.get_redirect_target(request.redirect_from_id)
        if existing_target is not None:
            raise HTTPException(status_code=409, detail="Redirect already exists")

        if self.vitess.is_entity_deleted(request.redirect_from_id):
            raise HTTPException(
                status_code=423, detail="Source entity has been deleted"
            )
        if self.vitess.is_entity_deleted(request.redirect_to_id):
            raise HTTPException(
                status_code=423, detail="Target entity has been deleted"
            )

        if self.vitess.is_entity_locked(
            request.redirect_to_id
        ) or self.vitess.is_entity_archived(request.redirect_to_id):
            raise HTTPException(
                status_code=423, detail="Target entity is locked or archived"
            )

        to_head_revision_id = self.vitess.get_head(request.redirect_to_id)
        if to_head_revision_id == 0:
            raise HTTPException(
                status_code=404, detail="Target entity has no revisions"
            )

        from_head_revision_id = self.vitess.get_head(request.redirect_from_id)
        redirect_revision_id = from_head_revision_id + 1 if from_head_revision_id else 1

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

        self.s3.write_revision(
            entity_id=request.redirect_from_id,
            revision_id=redirect_revision_id,
            data=redirect_revision_data,
            publication_state="pending",
        )

        self.vitess.insert_revision(
            request.redirect_from_id,
            redirect_revision_id,
            is_mass_edit=False,
            edit_type=EditType.REDIRECT_CREATE.value,
        )

        self.vitess.create_redirect(
            redirect_from_entity_id=request.redirect_from_id,
            redirect_to_entity_id=request.redirect_to_id,
            created_by=request.created_by,
        )

        self.vitess.set_redirect_target(
            entity_id=request.redirect_from_id,
            redirects_to_entity_id=request.redirect_to_id,
        )

        self.s3.mark_published(
            entity_id=request.redirect_from_id,
            revision_id=redirect_revision_id,
            publication_state="published",
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

        current_redirect_target = self.vitess.get_redirect_target(entity_id)

        if current_redirect_target is None:
            raise HTTPException(status_code=404, detail="Entity is not a redirect")

        if self.vitess.is_entity_deleted(entity_id):
            raise HTTPException(status_code=423, detail="Entity has been deleted")

        if self.vitess.is_entity_locked(entity_id) or self.vitess.is_entity_archived(
            entity_id
        ):
            raise HTTPException(status_code=423, detail="Entity is locked or archived")

        head_revision_id = self.vitess.get_head(entity_id)
        new_revision_id = head_revision_id + 1 if head_revision_id else 1

        target_revision = self.s3.read_full_revision(entity_id, revert_to_revision_id)
        target_data = target_revision["data"]

        new_revision_data = {
            "schema_version": "1.1.0",
            "redirects_to": None,
            "entity": target_data["entity"],
        }

        self.s3.write_revision(
            entity_id=entity_id,
            revision_id=new_revision_id,
            data=new_revision_data,
            publication_state="pending",
        )

        self.vitess.insert_revision(
            entity_id,
            new_revision_id,
            is_mass_edit=False,
            edit_type=EditType.REDIRECT_REVERT.value,
        )

        self.vitess.set_redirect_target(
            entity_id=entity_id,
            redirects_to_entity_id=None,
        )

        self.s3.mark_published(
            entity_id=entity_id,
            revision_id=new_revision_id,
            publication_state="published",
        )

        return EntityResponse(
            id=entity_id, revision_id=new_revision_id, data=new_revision_data["entity"]
        )
