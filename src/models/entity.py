from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EditType(str, Enum):
    """Standardized edit type classifications for filtering"""

    # Protection management
    LOCK_ADDED = "lock-added"
    LOCK_REMOVED = "lock-removed"
    SEMI_PROTECTION_ADDED = "semi-protection-added"
    SEMI_PROTECTION_REMOVED = "semi-protection-removed"
    ARCHIVE_ADDED = "archive-added"
    ARCHIVE_REMOVED = "archive-removed"

    # Mass edit classifications
    BOT_IMPORT = "bot-import"
    BOT_CLEANUP = "bot-cleanup"
    BOT_MERGE = "bot-merge"
    BOT_SPLIT = "bot-split"

    # Manual edit classifications
    MANUAL_CREATE = "manual-create"
    MANUAL_UPDATE = "manual-update"
    MANUAL_CORRECTION = "manual-correction"

    # Cleanup campaigns
    CLEANUP_2025 = "cleanup-2025"
    CLEANUP_LABELS = "cleanup-labels"
    CLEANUP_DESCRIPTIONS = "cleanup-descriptions"

    # Migration operations
    MIGRATION_INITIAL = "migration-initial"
    MIGRATION_BATCH = "migration-batch"

    # Deletion operations
    SOFT_DELETE = "soft-delete"
    HARD_DELETE = "hard-delete"
    UNDELETE = "undelete"
    
    # Redirect operations
    REDIRECT_CREATE = "redirect-create"
    REDIRECT_REVERT = "redirect-revert"

    # Default
    UNSPECIFIED = ""


class EntityCreateRequest(BaseModel):
    id: str = Field(..., description="Entity ID (e.g., Q42)")
    type: str = Field(default="item", description="Entity type")
    labels: Optional[Dict[str, Dict[str, str]]] = None
    descriptions: Optional[Dict[str, Dict[str, str]]] = None
    claims: Optional[Dict[str, List]] = None
    aliases: Optional[Dict[str, List]] = None
    sitelinks: Optional[Dict[str, Any]] = None
    is_mass_edit: bool = Field(default=False, description="Whether this is a mass edit")
    edit_type: str = Field(
        default="",
        description="Text classification of edit type (e.g., 'bot-import', 'cleanup')",
    )
    is_semi_protected: bool = Field(default=False, description="Item is semi-protected")
    is_locked: bool = Field(default=False, description="Item is locked from edits")
    is_archived: bool = Field(default=False, description="Item is archived")
    is_dangling: bool = Field(
        default=False,
        description="Item has no maintaining WikiProject (computed by frontend)",
    )
    is_mass_edit_protected: bool = Field(
        default=False, description="Item is protected from mass edits"
    )
    is_not_autoconfirmed_user: bool = Field(
        default=False, description="User is not autoconfirmed (new/unconfirmed account)"
    )

    model_config = ConfigDict(extra="allow")

    @property
    def data(self) -> Dict[str, Any]:
        """Return entity as dict for compatibility with existing code"""
        return self.model_dump(exclude_unset=True)


class EntityResponse(BaseModel):
    id: str
    revision_id: int
    data: Dict[str, Any]
    is_semi_protected: bool = False
    is_locked: bool = False
    is_archived: bool = False
    is_dangling: bool = False
    is_mass_edit_protected: bool = False


class RevisionMetadata(BaseModel):
    revision_id: int
    created_at: str


class DeleteType(str, Enum):
    """Deletion type classification"""

    SOFT = "soft"
    HARD = "hard"


class EntityDeleteRequest(BaseModel):
    delete_type: DeleteType = Field(
        default=DeleteType.SOFT, description="Type of deletion"
    )


class EntityDeleteResponse(BaseModel):
    id: str
    revision_id: int
    delete_type: DeleteType
    is_deleted: bool


class EntityRedirectRequest(BaseModel):
    redirect_from_id: str = Field(
        ..., description="Source entity ID to be marked as redirect (e.g., Q59431323)"
    )
    redirect_to_id: str = Field(
        ..., description="Target entity ID (e.g., Q42)"
    )
    created_by: str = Field(
        default="entity-api",
        description="User or system creating redirect"
    )


class EntityRedirectResponse(BaseModel):
    redirect_from_id: str
    redirect_to_id: str
    created_at: str
    revision_id: int


class RedirectRevertRequest(BaseModel):
    revert_to_revision_id: int = Field(
        ..., description="Revision ID to revert to (e.g., 12340)"
    )
    revert_reason: str = Field(
        ..., description="Reason for reverting redirect"
    )
    created_by: str = Field(default="entity-api")
