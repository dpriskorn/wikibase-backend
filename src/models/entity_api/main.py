import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from rapidhash import rapidhash

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from models.infrastructure.s3_client import S3Client
from models.infrastructure.ulid_flake import generate_ulid_flake
from models.infrastructure.vitess_client import VitessClient
from models.config.settings import settings
from models.entity import (
    DeleteType,
    EditType,
    EntityCreateRequest,
    EntityDeleteRequest,
    EntityDeleteResponse,
    EntityResponse,
    RevisionMetadata,
    EntityRedirectRequest,
    RedirectRevertRequest,
)

from services.entity_api.redirects import RedirectService

if TYPE_CHECKING:
    from models.infrastructure.s3_client import S3Config
    from models.infrastructure.vitess_client import VitessConfig


class Clients(BaseModel):
    s3: S3Client | None = None
    vitess: VitessClient | None = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, s3: "S3Config", vitess: "VitessConfig", **kwargs):
        super().__init__(s3=S3Client(s3), vitess=VitessClient(vitess), **kwargs)


# noinspection PyShadowingNames,PyUnresolvedReferences
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.clients = Clients(
        s3=settings.to_s3_config(), vitess=settings.to_vitess_config()
    )
    yield
    app.state.clients.s3 = None
    app.state.clients.vitess = None


app = FastAPI(lifespan=lifespan)


# noinspection PyUnresolvedReferences
@app.get("/health")
def health_check():
    clients = app.state.clients
    return {
        "status": "ok",
        "s3": "connected" if clients.s3 else "disconnected",
        "vitess": "connected" if clients.vitess else "disconnected",
    }


# noinspection PyUnresolvedReferences
@app.post("/entity", response_model=EntityResponse)
def create_entity(request: EntityCreateRequest):
    clients = app.state.clients

    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")

    entity_id = request.data.get("id")
    is_mass_edit = request.is_mass_edit if request.is_mass_edit is not None else False
    edit_type = request.edit_type if request.edit_type is not None else ""

    if not entity_id:
        raise HTTPException(status_code=400, detail="Entity must have 'id' field")

    internal_id = clients.vitess.resolve_id(entity_id)
    if internal_id is None:
        internal_id = generate_ulid_flake()
        clients.vitess.register_entity(entity_id, internal_id)
    else:
        # Check if entity is hard-deleted (block edits/undelete)
        if clients.vitess.is_entity_deleted(internal_id):
            raise HTTPException(
                status_code=410, detail=f"Entity {entity_id} has been deleted"
            )

    head_revision_id = clients.vitess.get_head(internal_id)

    # Calculate content hash for deduplication
    entity_json = json.dumps(request.data, sort_keys=True)
    content_hash = rapidhash(entity_json.encode())

    # Check if head revision has same content (idempotency)
    if head_revision_id is not None:
        try:
            head_revision = clients.s3.read_revision(entity_id, head_revision_id)
            if head_revision.data.get("content_hash") == content_hash:
                # Content unchanged, return existing revision
                return EntityResponse(
                    id=entity_id,
                    revision_id=head_revision_id,
                    data=request.data,
                    is_semi_protected=head_revision.data.get(
                        "is_semi_protected", False
                    ),
                    is_locked=head_revision.data.get("is_locked", False),
                    is_archived=head_revision.data.get("is_archived", False),
                    is_dangling=head_revision.data.get("is_dangling", False),
                )
        except Exception:
            # Head revision not found or invalid, proceed with creation
            pass

    # Check protection permissions
    if head_revision_id is not None:
        try:
            current = clients.s3.read_revision(entity_id, head_revision_id)

            # Archived items block all edits
            if current.data.get("is_archived"):
                raise HTTPException(403, "Item is archived and cannot be edited")

            # Locked items block all edits
            if current.data.get("is_locked"):
                raise HTTPException(403, "Item is locked from all edits")

            # Mass-edit protection blocks mass edits only
            if current.data.get("is_mass_edit_protected") and request.is_mass_edit:
                raise HTTPException(403, "Mass edits blocked on this item")

            # Semi-protection blocks not-autoconfirmed users
            if (
                current.data.get("is_semi_protected")
                and request.is_not_autoconfirmed_user
            ):
                raise HTTPException(
                    403,
                    "Semi-protected items cannot be edited by new or unconfirmed users",
                )
        except HTTPException:
            raise
        except Exception:
            pass

    new_revision_id = head_revision_id + 1 if head_revision_id else 1

    # Construct full revision schema with content hash
    revision_data = {
        "schema_version": settings.s3_revision_schema_version,
        "revision_id": new_revision_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "created_by": "entity-api",
        "is_mass_edit": is_mass_edit,
        "edit_type": edit_type or EditType.UNSPECIFIED.value,
        "entity_type": request.data.get("type", "item"),
        "is_semi_protected": request.is_semi_protected,
        "is_locked": request.is_locked,
        "is_archived": request.is_archived,
        "is_dangling": request.is_dangling,
        "is_mass_edit_protected": request.is_mass_edit_protected,
        "is_deleted": False,
        "is_redirect": False,
        "entity": request.data,
        "content_hash": content_hash,
    }

    clients.s3.write_revision(
        entity_id=entity_id,
        revision_id=new_revision_id,
        data=revision_data,
        publication_state="pending",
    )
    clients.vitess.insert_revision(
        internal_id,
        new_revision_id,
        is_mass_edit,
        edit_type or EditType.UNSPECIFIED.value,
    )

    if head_revision_id is None:
        success = clients.vitess.insert_head_with_status(
            internal_id,
            new_revision_id,
            request.is_semi_protected,
            request.is_locked,
            request.is_archived,
            request.is_dangling,
            request.is_mass_edit_protected,
            is_deleted=False,
        )
    else:
        success = clients.vitess.cas_update_head_with_status(
            internal_id,
            head_revision_id,
            new_revision_id,
            request.is_semi_protected,
            request.is_locked,
            request.is_archived,
            request.is_dangling,
            request.is_mass_edit_protected,
            is_deleted=False,
        )

    if not success:
        raise HTTPException(status_code=409, detail="Concurrent modification detected")

    clients.s3.mark_published(
        entity_id=entity_id,
        revision_id=new_revision_id,
        publication_state="published",
    )

    return EntityResponse(
        id=entity_id,
        revision_id=new_revision_id,
        data=request.data,
        is_semi_protected=request.is_semi_protected,
        is_locked=request.is_locked,
        is_archived=request.is_archived,
        is_dangling=request.is_dangling,
        is_mass_edit_protected=request.is_mass_edit_protected,
    )


# noinspection PyUnresolvedReferences
@app.get("/entity/{entity_id}", response_model=EntityResponse)
def get_entity(entity_id: str):
    clients = app.state.clients

    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")

    internal_id = clients.vitess.resolve_id(entity_id)
    if internal_id is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    head_revision_id = clients.vitess.get_head(internal_id)
    if head_revision_id is None:
        raise HTTPException(status_code=404, detail="Entity has no revisions")

    # Check if entity is hard-deleted
    if clients.vitess.is_entity_deleted(internal_id):
        raise HTTPException(
            status_code=410, detail=f"Entity {entity_id} has been deleted"
        )

    if clients.s3 is None:
        raise HTTPException(status_code=503, detail="S3 not initialized")

    revision = clients.s3.read_revision(entity_id, head_revision_id)

    # Extract entity from full revision schema (data is already parsed dict)
    entity_data = revision.data["entity"]

    return EntityResponse(
        id=entity_id,
        revision_id=head_revision_id,
        data=entity_data,
        is_semi_protected=revision.data.get("is_semi_protected", False),
        is_locked=revision.data.get("is_locked", False),
        is_archived=revision.data.get("is_archived", False),
        is_dangling=revision.data.get("is_dangling", False),
        is_mass_edit_protected=revision.data.get("is_mass_edit_protected", False),
    )


# noinspection PyUnresolvedReferences
@app.get("/entity/{entity_id}/history", response_model=list[RevisionMetadata])
def get_entity_history(entity_id: str):
    clients = app.state.clients

    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")

    internal_id = clients.vitess.resolve_id(entity_id)
    if internal_id is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    history = clients.vitess.get_history(internal_id)

    return [
        RevisionMetadata(revision_id=record.revision_id, created_at=record.created_at)
        for record in history
    ]


# noinspection PyUnresolvedReferences
@app.get("/wiki/Special:EntityData/{entity_id}.ttl")
async def get_entity_data_turtle(entity_id: str):
    clients = app.state.clients

    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")

    internal_id = clients.vitess.resolve_id(entity_id)
    if internal_id is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    head_revision_id = clients.vitess.get_head(internal_id)
    if head_revision_id is None:
        raise HTTPException(status_code=404, detail="Entity has no revisions")

    revision = clients.s3.read_revision(entity_id, head_revision_id)
    entity_data = revision.data["entity"]

    turtle = serialize_entity_to_turtle(entity_data, entity_id)
    return Response(content=turtle, media_type="text/turtle")


@app.post("/redirects")
async def create_entity_redirect(request: EntityRedirectRequest):
    """Create a redirect from one entity to another"""
    clients = app.state.clients
    redirect_service = RedirectService(clients.s3, clients.vitess)
    return redirect_service.create_redirect(request)


@app.post("/entities/{entity_id}/revert-redirect")
async def revert_entity_redirect(entity_id: str, request: RedirectRevertRequest):
    """Revert a redirect entity back to normal using revision-based restore"""
    clients = app.state.clients
    redirect_service = RedirectService(clients.s3, clients.vitess)
    return redirect_service.revert_redirect(entity_id, request.revert_to_revision_id)


# noinspection PyUnresolvedReferences
@app.get("/entity/{entity_id}/revision/{revision_id}", response_model=Dict[str, Any])
def get_entity_revision(entity_id: str, revision_id: int):
    clients = app.state.clients

    if clients.s3 is None:
        raise HTTPException(status_code=503, detail="S3 not initialized")

    revision = clients.s3.read_revision(entity_id, revision_id)

    # Extract entity from full revision schema (data is already parsed dict)
    entity_data = revision.data["entity"]

    return entity_data


# noinspection PyUnresolvedReferences
@app.delete("/entity/{entity_id}", response_model=EntityDeleteResponse)
def delete_entity(entity_id: str, request: EntityDeleteRequest):
    """Delete entity (soft or hard delete)"""
    clients = app.state.clients

    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")

    # Resolve entity ID
    internal_id = clients.vitess.resolve_id(entity_id)
    if internal_id is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Get current head revision
    head_revision_id = clients.vitess.get_head(internal_id)
    if head_revision_id is None:
        raise HTTPException(status_code=404, detail="Entity has no revisions")

    if clients.s3 is None:
        raise HTTPException(status_code=503, detail="S3 not initialized")

    # Read current revision to preserve entity data
    current_revision = clients.s3.read_revision(entity_id, head_revision_id)

    # Calculate next revision ID
    new_revision_id = head_revision_id + 1

    # Prepare deletion revision data
    deleted_at = datetime.utcnow().isoformat() + "Z"
    edit_type = (
        EditType.SOFT_DELETE.value
        if request.delete_type == DeleteType.SOFT
        else EditType.HARD_DELETE.value
    )

    revision_data = {
        "schema_version": settings.s3_revision_schema_version,
        "revision_id": new_revision_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "created_by": "entity-api",
        "is_mass_edit": False,
        "edit_type": edit_type,
        "entity_type": current_revision.data.get("entity_type", "item"),
        "is_semi_protected": current_revision.data.get("is_semi_protected", False),
        "is_locked": current_revision.data.get("is_locked", False),
        "is_archived": current_revision.data.get("is_archived", False),
        "is_dangling": current_revision.data.get("is_dangling", False),
        "is_mass_edit_protected": current_revision.data.get(
            "is_mass_edit_protected", False
        ),
        "is_deleted": True,
        "is_redirect": False,
        "entity": current_revision.data.get("entity", {}),
    }

    # Write deletion revision to S3
    clients.s3.write_revision(
        entity_id=entity_id,
        revision_id=new_revision_id,
        data=revision_data,
        publication_state="pending",
    )

    # Insert revision metadata into Vitess
    clients.vitess.insert_revision(
        internal_id, new_revision_id, is_mass_edit=False, edit_type=edit_type
    )

    # Handle hard delete
    if request.delete_type == DeleteType.HARD:
        clients.vitess.hard_delete_entity(
            internal_id=internal_id,
            entity_id=entity_id,
            head_revision_id=new_revision_id,
        )
    else:
        # For soft delete, update head pointer with CAS
        success = clients.vitess.cas_update_head_with_status(
            internal_id,
            head_revision_id,
            new_revision_id,
            current_revision.data.get("is_semi_protected", False),
            current_revision.data.get("is_locked", False),
            current_revision.data.get("is_archived", False),
            current_revision.data.get("is_dangling", False),
            current_revision.data.get("is_mass_edit_protected", False),
            is_deleted=False,
        )

        if not success:
            raise HTTPException(
                status_code=409, detail="Concurrent modification detected"
            )

    # Mark as published
    clients.s3.mark_published(
        entity_id=entity_id,
        revision_id=new_revision_id,
        publication_state="published",
    )

    return EntityDeleteResponse(
        id=entity_id,
        revision_id=new_revision_id,
        delete_type=request.delete_type,
        is_deleted=True,
    )


# noinspection PyUnresolvedReferences
@app.get("/raw/{entity_id}/{revision_id}")
def get_raw_revision(entity_id: str, revision_id: int):
    """
    Returns raw S3 entity data for specific revision.

    Pure S3 data - no wrapper, no transformation.

    Returns 404 with typed error_type if:
    - Entity doesn't exist in ID mapping (ENTITY_NOT_FOUND)
    - Entity has no revisions (NO_REVISIONS)
    - Requested revision doesn't exist (REVISION_NOT_FOUND)
    """
    clients = app.state.clients

    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")

    # Check if entity exists
    internal_id = clients.vitess.resolve_id(entity_id)
    if internal_id is None:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_id} not found in ID mapping"
        )

    # Check if revisions exist for entity
    history = clients.vitess.get_history(internal_id)
    if not history:
        raise HTTPException(
            status_code=404, detail=f"Entity {entity_id} has no revisions"
        )

    # Check if requested revision exists
    revision_ids = [r.revision_id for r in history]
    if revision_id not in revision_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Revision {revision_id} not found for entity {entity_id}. Available revisions: {revision_ids}",
        )

    # Read full revision schema from S3
    if clients.s3 is None:
        raise HTTPException(status_code=503, detail="S3 not initialized")

    revision = clients.s3.read_full_revision(entity_id, revision_id)

    # Return full revision as-is (no transformation)
    return revision


# noinspection PyUnresolvedReferences
@app.get("/entities")
def list_entities(
    status: Optional[str] = None, edit_type: Optional[str] = None, limit: int = 100
):
    """Filter entities by status or edit_type"""
    clients = app.state.clients

    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")

    if status == "locked":
        return clients.vitess.list_locked_entities(limit)
    elif status == "semi_protected":
        return clients.vitess.list_semi_protected_entities(limit)
    elif status == "archived":
        return clients.vitess.list_archived_entities(limit)
    elif status == "dangling":
        return clients.vitess.list_dangling_entities(limit)
    elif edit_type:
        return clients.vitess.list_by_edit_type(edit_type, limit)
    else:
        raise HTTPException(
            status_code=400, detail="Must provide status or edit_type filter"
        )
