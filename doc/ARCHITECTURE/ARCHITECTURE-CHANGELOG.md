# Architecture Changelog

This file tracks architectural changes, feature additions, and modifications to wikibase-backend system.

## [2025-01-02] Internal ID Encapsulation

### Summary

Encapsulated internal ID resolution within VitessClient, removing exposure of internal IDs to all external code. All VitessClient methods now accept `entity_id: str` instead of `internal_id: int`, handling ID resolution internally. This aligns with the goal of keeping internal implementation details private and maintaining clean API boundaries.

### Motivation

- **Encapsulation**: Internal IDs are implementation details that shouldn't leak outside VitessClient
- **API cleanliness**: External code should work with entity IDs only (Q42, not internal ID 42)
- **Maintainability**: Changes to internal ID handling only affect VitessClient, not all calling code
- **Testing**: Simpler tests - no need to manage internal ID mappings

### Changes

#### VitessClient API Updates

**File**: `src/models/infrastructure/vitess_client.py`

**Private method**:
- `resolve_id()` → `_resolve_id()`: Made private to prevent external access

**Method signature changes** (all now accept `entity_id: str` instead of `internal_id: int`):
- `is_entity_deleted(entity_id: str)`: Check if entity is hard-deleted
- `is_entity_locked(entity_id: str)`: Check if entity is locked
- `is_entity_archived(entity_id: str)`: Check if entity is archived
- `get_head(entity_id: str)`: Get current head revision
- `write_entity_revision(entity_id: str, ...)`: Write revision data
- `read_full_revision(entity_id: str, revision_id: int)`: Read revision data
- `insert_revision(entity_id: str, ...)`: Insert revision metadata
- `get_redirect_target(entity_id: str)`: Get redirect target
- `set_redirect_target(entity_id: str, redirects_to_entity_id: str | None)`: Set redirect target
- `get_history(entity_id: str)`: Get revision history
- `hard_delete_entity(entity_id: str, head_revision_id: int)`: Permanently delete entity

**Internal behavior**:
- All methods now call `_resolve_id(entity_id)` internally to convert to internal IDs
- Methods validate entity exists and return sensible defaults (False, [], 0) if not found
- Methods that require valid entities raise `ValueError` with descriptive message

#### RedirectService Updates

**File**: `src/services/entity_api/redirects.py`

**Removed calls**:
- No longer calls `vitess.resolve_id()` directly
- No longer manages `from_internal_id` and `to_internal_id` variables

**Updated flow**:
- All VitessClient calls use `entity_id: str` parameters
- VitessClient handles all internal ID resolution
- Simplified validation logic - no need to check for `None` internal IDs

#### Entity API Updates

**File**: `src/models/entity_api/main.py`

**Removed calls**:
- No longer calls `clients.vitess.resolve_id()` directly
- `internal_id` variables replaced with direct entity_id usage

**Updated methods**:
- All VitessClient calls now pass entity IDs directly
- Removed manual internal ID resolution logic

#### Test Mocks Updates

**File**: `tests/test_entity_redirects.py`

**Updated MockVitessClient**:
- `_resolve_id()` made private (mocks match real API)
- Methods updated to accept `entity_id: str` parameters
- Internal ID resolution happens within mock methods

**Updated Mock RedirectService**:
- Removed `from_internal_id` and `to_internal_id` tracking
- All operations use entity IDs only

### Rationale

- **Encapsulation**: Internal IDs are Vitess implementation detail, not API surface
- **Type safety**: Strings (entity IDs) are less error-prone than mixing int/str IDs
- **Simplification**: External code doesn't need to understand internal ID mapping
- **Testability**: Tests focus on entity IDs, not implementation details
- **Future-proof**: If internal ID scheme changes, only VitessClient needs updates

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

**Updated VitessClient methods**:
- `resolve_id()` → `_resolve_id()`: Made private (internal ID resolution no longer exposed)
- `set_redirect_target()`: Mark entity as redirect in entity_head (now accepts `entity_id: str`)
- `create_redirect()`: Create redirect relationship in entity_redirects table (now accepts `entity_id: str`)
- `get_incoming_redirects()`: Query entities redirecting to target (for RDF builder) (now accepts `entity_id: str`)
- `get_redirect_target()`: Query where entity redirects to (for validation) (now accepts `entity_id: str`)
- `is_entity_deleted()`: Check if entity is hard-deleted (now accepts `entity_id: str`)
- `is_entity_locked()`: Check if entity is locked (now accepts `entity_id: str`)
- `is_entity_archived()`: Check if entity is archived (now accepts `entity_id: str`)
- `get_head()`: Get current head revision (now accepts `entity_id: str`)
- `write_entity_revision()`: Write revision data (now accepts `entity_id: str`)
- `read_full_revision()`: Read revision data (now accepts `entity_id: str`)
- `insert_revision()`: Insert revision metadata (now accepts `entity_id: str`)
- `get_history()`: Get revision history (now accepts `entity_id: str`)
- `hard_delete_entity()`: Permanently delete entity (removed `internal_id` parameter)

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
  - Validates both entities exist (using Vitess, no internal ID exposure)
  - Prevents circular redirects
  - Checks for duplicate redirects (using Vitess)
  - Validates target not already a redirect
  - Validates source and target not deleted/locked/archived
  - Creates minimal S3 revision (tombstone) for redirect entity
  - Records redirect in Vitess (Vitess handles internal ID resolution internally)
  - Updates entity_head.redirects_to for source entity
  - Returns revision ID of redirect entity

- `revert_redirect()`: Revert redirect entity back to normal
  - Reads current redirect revision (tombstone)
  - Reads target entity revision to restore from
  - Writes new revision with full entity data
  - Updates entity_head.redirects_to to null (Vitess handles internal ID resolution)
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
  "is_deleted": true,
  "is_redirect": false,
  "deletion_reason": "Privacy request",
  "deleted_at": "2025-12-28T10:30:00Z",
  "deleted_by": "admin-user",
  "entity": {...}
}
```

**Fields**:
- `is_deleted`: Boolean flag indicating if revision is a deletion tombstone
- `is_redirect`: Boolean flag indicating if entity is a redirect
- `deletion_reason`: Human-readable reason for deletion (required if is_deleted=true)
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
ALTER TABLE entity_head ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE entity_head ADD COLUMN is_redirect BOOLEAN DEFAULT FALSE;
```

**Rationale**:
- `is_deleted` flag in entity_head enables fast filtering of hard-deleted entities
- `is_redirect` flag in entity_head enables fast checking of redirect status
- Deletion metadata stored in revision snapshots for complete audit trail

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
