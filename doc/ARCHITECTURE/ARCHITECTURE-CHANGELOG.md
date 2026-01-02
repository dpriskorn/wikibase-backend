# Architecture Changelog

This file tracks architectural changes, feature additions, and modifications to the wikibase-backend system.

## [2025-01-15] Entity Redirect Support

### Summary

Added redirect entity support allowing creation of redirect relationships between entities. Redirects are minimal tombstones pointing to target entities, following the immutable revision pattern. Support includes S3 schema for redirect metadata, Vitess tables for tracking relationships, Entity API for creating redirects, special revert endpoint for undoing redirects, and RDF builder integration for efficient querying.

### Motivation

Wikibase requires redirect functionality for:
- **Entity merges**: When two items are merged, source becomes a redirect to target
- **Stable identifiers**: Preserve old entity IDs that may be referenced externally
- **RDF compliance**: Generate `owl:sameAs` statements matching Wikidata format
- **Revertibility**: Redirects can be reverted back to normal entities using revision-based restore
- **Vitess efficiency**: RDF builder queries Vitess for redirect counts instead of MediaWiki API
- **Community needs**: Easy reversion to earlier entity states before redirect was created

### Changes

#### Updated S3 Revision Schema

**File**: `src/schemas/s3-revision/1.1.0/schema.json`

Added redirect metadata field:

```json
{
  "redirects_to": "Q42"  // or null for normal entities
}
```

Redirect entities have minimal structure:

```json
{
  "redirects_to": "Q42",
  "entity": {
    "id": "Q59431323",
    "labels": {},
    "descriptions": {},
    "aliases": {},
    "claims": {},
    "sitelinks": {}
  }
}
```

**Schema version bump**: 1.0.0 → 1.1.0 (MINOR - backward-compatible addition)

**Rationale**:
- `redirects_to`: Single entity ID or null, marking redirect target (or null)
- Redirect entities have empty labels, claims, sitelinks (minimal tombstone)
- Can be reverted by writing new revision with `redirects_to: null` and full entity data
- Backward compatible (null for normal entities in 1.0.0)

#### Updated Vitess Schema

**File**: `src/models/infrastructure/vitess_client.py`

**Add to entity_head table**:

```sql
ALTER TABLE entity_head ADD COLUMN redirects_to BIGINT NULL;
```

**New table: entity_redirects**

```sql
CREATE TABLE IF NOT EXISTS entity_redirects (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    redirect_from_id BIGINT NOT NULL,
    redirect_to_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) DEFAULT NULL,
    INDEX idx_redirect_from (redirect_from_id),
    INDEX idx_redirect_to (redirect_to_id),
    UNIQUE KEY unique_redirect (redirect_from_id, redirect_to_id)
)
```

**New VitessClient methods**:
- `set_redirect_target()`: Mark entity as redirect in entity_head
- `create_redirect()`: Create redirect relationship in entity_redirects table
- `get_incoming_redirects()`: Query entities redirecting to target (for RDF builder)
- `get_redirect_target()`: Query where entity redirects to (for validation)

**Rationale**:
- `redirects_to` in entity_head: Fast check if entity is a redirect
- Separate `entity_redirects` table: Track all redirect relationships without bloating entity_head
- Bidirectional indexes: Support both incoming (RDF builder) and target (validation) queries
- Audit trail: `created_at` and `created_by` track redirect creation
- Unique constraint: Prevent duplicate redirects

#### Entity Model Updates

**File**: `src/models/entity.py`

**New models**:
```python
class EntityRedirectRequest(BaseModel):
    redirect_from_id: str  # Entity to mark as redirect (e.g., Q59431323)
    redirect_to_id: str    # Target entity (e.g., Q42)
    created_by: str = "entity-api"

class EntityRedirectResponse(BaseModel):
    redirect_from_id: str
    redirect_to_id: str
    redirect_from_internal_id: int
    redirect_to_internal_id: int
    created_at: str
    revision_id: int
```

**New EditType values**:
- `REDIRECT_CREATE = "redirect-create"`: Creating a redirect
- `REDIRECT_REVERT = "redirect-revert"`: Converting redirect back to normal entity

**Revert support models**:
```python
class RedirectRevertRequest(BaseModel):
    revert_to_revision_id: int = Field(
        ..., description="Revision ID to revert to (e.g., 12340)"
    )
    revert_reason: str = Field(
        ..., description="Reason for reverting redirect"
    )
    created_by: str = Field(default="entity-api")
```

#### Entity API Integration

**New File**: `src/services/entity_api/redirects.py`

**New RedirectService**:
- `create_redirect()`: Mark entity as redirect
  - Validates both entities exist (using Vitess)
  - Prevents circular redirects
  - Checks for duplicate redirects (using Vitess)
  - Validates target not already a redirect
  - Validates source and target not deleted/locked/archived
  - Creates minimal S3 revision (tombstone) for redirect entity
  - Records redirect in Vitess
  - Updates entity_head.redirects_to for source entity
  - Returns revision ID of redirect entity

- `revert_redirect()`: Revert redirect entity back to normal
  - Reads current redirect revision (tombstone)
  - Reads target entity revision to restore from
  - Writes new revision with full entity data
  - Updates entity_head.redirects_to to null
  - Returns new revision ID

**New FastAPI endpoints**: 
- `POST /entities/redirects`: Create redirect
- `POST /entities/{id}/revert-redirect`: Revert redirect back to normal

**Request/Response**: 
- `EntityRedirectRequest` → `EntityRedirectResponse`
- `RedirectRevertRequest` → `EntityResponse`

#### RDF Builder Enhancements

**File**: `src/models/rdf_builder/converter.py`

**Changes**:
- Added `vitess_client` parameter to `EntityConverter.__init__()`
- Updated `_fetch_redirects()` to query Vitess for redirects
- Maintains fallback to file-based cache for test scenarios
- Priority: Vitess → File cache → Empty list

**File**: `src/models/rdf_builder/redirect_cache.py`

**New method**:
```python
def load_entity_redirects_from_vitess(
    entity_id: str, vitess_client: VitessClient
) -> list[str]:
    """Load redirects from Vitess authoritative data source"""
```

**Rationale**:
- RDF builder queries Vitess for redirects (authoritative source)
- Eliminates MediaWiki API dependency in production
- File-based cache still works for test scenarios
- Support efficient redirect count queries for UI

### Impact

- **RDF Builder**: Queries Vitess for redirects (authoritative source), no MediaWiki dependency
- **Entity API**: Can create/revert redirects via S3 + Vitess (immutable snapshots)
- **Readers**: Redirects visible in S3 revision history, queryable via Vitess
- **Revertibility**: Redirects can be undone by writing new revision with normal entity data using revision-based restore
- **Query Performance**: Indexed Vitess lookups (O(log n) for large entity sets)
- **Vitess Awareness**: Vitess knows redirect counts (e.g., Q42 has 4 incoming redirects)

### Backward Compatibility

- Schema 1.1.0 is backward compatible with 1.0.0 (redirects_to field optional)
- Normal entities have `redirects_to: null` (or omitted)
- Redirect entities have minimal entity structure + `redirects_to` field
- Existing readers ignore unknown fields
- RDF builder falls back to file cache if Vitess unavailable

### Future Enhancements

- Update target entity S3 revision to include new redirect in `redirects` array (currently no-op)
- Batch redirect creation for mass merges
- Redirect chain validation (detect circular multi-hop)
- Redirect deletion/undo operations
- Redirect statistics and metrics API
- Redirect import/export operations for bulk data migration

---

## [2025-12-28] Entity Deletion (Soft and Hard Delete)

### Summary

Added entity deletion functionality supporting both soft deletes (default) and hard deletes (exceptional). Soft deletes create tombstone revisions preserving entity history, while hard deletes mark entities as hidden with full audit trail.

### Motivation

Wikibase requires deletion capabilities for:
- Removing inappropriate content
- Privacy/GDPR compliance
- Data cleanup operations
- Removing test/duplicate entities
- Handling user deletion requests

### Changes

#### Updated S3 Revision Schema

**File**: `src/schemas/s3-revision/1.0.0/schema.json`

Added deletion-related fields to revision schema:

```json
{
  "deleted": true,
  "deletion_reason": "Privacy request",
  "deleted_at": "2025-12-28T10:30:00Z",
  "deleted_by": "admin-user",
  "entity": {...}
}
```

**Fields**:
- `deleted`: Boolean flag indicating if revision is a deletion tombstone
- `deletion_reason`: Human-readable reason for deletion (required if deleted=true)
- `deleted_at`: ISO-8601 timestamp of deletion action
- `deleted_by`: User or system that requested deletion

**Rationale**:
- Soft delete preserves entity data in `entity` field for audit/history
- Deletion metadata stored in revision snapshot for complete trail
- `deleted_at` separate from `created_at` for clarity

#### Updated Vitess Schema

**File**: `src/infrastructure/vitess_client.py` - `_create_tables()` method

**Changes to entity_head table**:
```sql
ALTER TABLE entity_head ADD COLUMN deleted BOOLEAN DEFAULT FALSE;
```

**New entity_delete_audit table**:
```sql
CREATE TABLE IF NOT EXISTS entity_delete_audit (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    entity_id BIGINT NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    delete_type ENUM('soft', 'hard') NOT NULL,
    deletion_reason TEXT,
    deleted_by VARCHAR(255),
    deleted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    head_revision_id BIGINT,
    INDEX idx_entity_id (entity_id),
    INDEX idx_deleted_at (deleted_at),
    INDEX idx_delete_type (delete_type)
)
```

**Rationale**:
- `deleted` flag in entity_head enables fast filtering of hard-deleted entities
- Separate audit table prevents bloating entity_head with deletion metadata
- Indexes support reporting queries (e.g., deletion metrics, compliance reports)
- Hard deletes are rare/exceptional - audit table is appropriate scale

#### New Pydantic Models

**File**: `src/services/shared/models/entity.py`

Added new models and enums:

```python
class DeleteType(str, Enum):
    SOFT = "soft"
    HARD = "hard"

class EntityDeleteRequest(BaseModel):
    delete_type: DeleteType = Field(default=DeleteType.SOFT)
    deletion_reason: str = Field(..., description="Reason for deletion")
    deleted_by: str = Field(..., description="User requesting deletion")

class EntityDeleteResponse(BaseModel):
    id: str
    revision_id: int
    delete_type: DeleteType
    deleted: bool
    deleted_at: str
    deletion_reason: str
    deleted_by: str
```

### Impact

- Readers: Initial implementation
- Writers: Initial implementation
- Migration: N/A (baseline schema)

### Notes

- Establishes canonical JSON format for immutable S3 snapshots
- Entity ID stored in S3 path and entity.id, not metadata
- `revision_id` must be monotonic per entity
- `content_hash` provides integrity verification and idempotency
