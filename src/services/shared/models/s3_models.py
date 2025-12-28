from typing import Any, Dict
from pydantic import BaseModel


class S3Config(BaseModel):
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str


class RevisionMetadata(BaseModel):
    key: str


class RevisionResponse(BaseModel):
    data: str


class RevisionCreateRequest(BaseModel):
    entity_id: str
    revision_id: int
    data: str
    publication_state: str = "pending"


class RevisionReadResponse(BaseModel):
    entity_id: str
    revision_id: int
    data: Dict[str, Any]


class RevisionUpdateRequest(BaseModel):
    entity_id: str
    revision_id: int
    publication_state: str
