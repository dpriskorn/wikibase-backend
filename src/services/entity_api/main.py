import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from rapidhash import rapidhash

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from infrastructure.s3_client import S3Client
from infrastructure.ulid_flake import generate_ulid_flake
from infrastructure.vitess_client import VitessClient
from services.shared.config.settings import settings
from services.shared.models.entity import (
    EntityCreateRequest,
    EntityResponse,
    RevisionMetadata
)

if TYPE_CHECKING:
    from infrastructure.s3_client import S3Config
    from infrastructure.vitess_client import VitessConfig


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
        s3=settings.to_s3_config(),
        vitess=settings.to_vitess_config()
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
        "vitess": "connected" if clients.vitess else "disconnected"
    }


# noinspection PyUnresolvedReferences
@app.post("/entity", response_model=EntityResponse)
def create_entity(request: EntityCreateRequest):
    clients = app.state.clients
    
    if clients.vitess is None:
        raise HTTPException(status_code=503, detail="Vitess not initialized")
    
    external_id = request.data.get("id")
    if not external_id:
        raise HTTPException(status_code=400, detail="Entity must have 'id' field")
    
    internal_id = clients.vitess.resolve_id(external_id)
    if internal_id is None:
        internal_id = generate_ulid_flake()
        clients.vitess.register_entity(external_id, internal_id)
    
    head_revision_id = clients.vitess.get_head(internal_id)
    
    # Calculate content hash for deduplication
    entity_json = json.dumps(request.data, sort_keys=True)
    content_hash = rapidhash(entity_json.encode())
    
    # Check if head revision has same content (idempotency)
    if head_revision_id is not None:
        try:
            head_revision = clients.s3.read_revision(external_id, head_revision_id)
            if head_revision.data.get("content_hash") == content_hash:
                # Content unchanged, return existing revision
                return EntityResponse(id=external_id, revision_id=head_revision_id, data=request.data)
        except Exception:
            # Head revision not found or invalid, proceed with creation
            pass
    
    new_revision_id = head_revision_id + 1 if head_revision_id else 1
    
    # Construct full revision schema with content hash
    revision_data = {
        "schema_version": settings.s3_revision_schema_version,
        "revision_id": new_revision_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "created_by": "entity-api",
        "entity_type": request.data.get("type", "item"),
        "entity": request.data,
        "content_hash": content_hash
    }
    
    clients.s3.write_revision(
        entity_id=external_id,
        revision_id=new_revision_id,
        data=revision_data,
        publication_state="pending"
    )
    clients.vitess.insert_revision(internal_id, new_revision_id)
    
    success = clients.vitess.cas_update_head(internal_id, head_revision_id, new_revision_id)
    if not success:
        raise HTTPException(status_code=409, detail="Concurrent modification detected")
    
    clients.s3.mark_published(
        entity_id=external_id,
        revision_id=new_revision_id,
        publication_state="published"
    )
    
    return EntityResponse(id=external_id, revision_id=new_revision_id, data=request.data)


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
    
    if clients.s3 is None:
        raise HTTPException(status_code=503, detail="S3 not initialized")
    
    revision = clients.s3.read_revision(entity_id, head_revision_id)
    
    # Extract entity from full revision schema (data is already parsed dict)
    entity_data = revision.data["entity"]
    
    return EntityResponse(id=entity_id, revision_id=head_revision_id, data=entity_data)


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
    
    return [RevisionMetadata(revision_id=record.revision_id, created_at=record.created_at) for record in history]


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
            status_code=404,
            detail=f"Entity {entity_id} not found in ID mapping"
        )
    
    # Check if revisions exist for entity
    history = clients.vitess.get_history(internal_id)
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"Entity {entity_id} has no revisions"
        )
    
    # Check if requested revision exists
    revision_ids = [r.revision_id for r in history]
    if revision_id not in revision_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Revision {revision_id} not found for entity {entity_id}. Available revisions: {revision_ids}"
        )
    
    # Read full revision schema from S3
    if clients.s3 is None:
        raise HTTPException(status_code=503, detail="S3 not initialized")
    
    revision = clients.s3.read_full_revision(entity_id, revision_id)
    
    # Return full revision as-is (no transformation)
    return revision
