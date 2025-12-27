from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict


class EntityCreateRequest(BaseModel):
    data: Dict[str, Any]


class EntityResponse(BaseModel):
    id: str
    revision_id: int
    data: Dict[str, Any]


class RevisionMetadata(BaseModel):
    revision_id: int
    created_at: str


class RawRevisionErrorType(str, Enum):
    """Enum for raw revision endpoint error types"""
    ENTITY_NOT_FOUND = "entity_not_found"
    NO_REVISIONS = "no_revisions"
    REVISION_NOT_FOUND = "revision_not_found"


class RawRevisionErrorResponse(BaseModel):
    """Error response for raw revision endpoint"""
    detail: str = Field(description="Human-readable error message")
    error_type: RawRevisionErrorType = Field(description="Machine-readable error type")
