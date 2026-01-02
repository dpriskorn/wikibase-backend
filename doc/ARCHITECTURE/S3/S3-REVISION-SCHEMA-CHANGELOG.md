# S3 Entity JSON Schema Changes

This document tracks all S3 entity JSON schema version changes for Wikibase immutable revision system.

## Quick Reference

| Version | Date | Type | Status |
|---------|------|------|--------|
| 1.1 | 2025-01-15 | Minor | Current |
| 1.0 | 2025-12-28 | Major | Previous |

---

## 1.0 - Major

**Status:** Current

### Changes

- Initial schema definition for entity JSON snapshots stored in S3
- Rapidhash integer for deduplication and integrity verification

### Schema

```json
{
  "schema_version": "1.0.0",
  "revision_id": 1,
  "created_at": "2025-01-15T10:30:00Z",
  "created_by": "entity-api",
  "entity_type": "item",
  "content_hash": 1234567890123456789,
  "entity": {
    "id": "Q42",
    "type": "item",
    "labels": {},
    "descriptions": {},
    "aliases": {},
    "claims": {},
    "sitelinks": {}
  }
}
```

### Metadata Fields

- `schema_version`: Schema version identifier (MAJOR.MINOR.PATCH)
- `revision_id`: Monotonic integer per entity
- `created_at`: ISO-8601 timestamp
- `created_by`: User or system identifier
- `entity_type`: Entity type (item/property/lexeme)
- `is_mass_edit`: Boolean flag for mass edit classification
- `content_hash`: Rapidhash integer for deduplication
- `edit_type`: Text classification of edit type (e.g., 'bot-import', 'cleanup-2025', 'lock-added')
- `is_semi_protected`: Boolean for semi-protection status (locked from mass-edits only)
- `is_locked`: Boolean for lock status (locked from all edits)
- `is_archived`: Boolean for archive status (cannot be edited, can be excluded from exports)
- `is_dangling`: Boolean for dangling status (no maintaining WikiProject, computed by frontend)

### Data Integrity

- Entity ID validated from S3 path and entity.id field
- Content hash detects duplicate submissions (idempotency)
- Snapshots are immutable - no modifications allowed

### Impact

- Readers: Initial implementation
- Writers: Initial implementation
- Migration: N/A (baseline schema)

### Notes

- Establishes canonical JSON format for immutable S3 snapshots
- Entity ID stored in S3 path and entity.id, not metadata
- `revision_id` must be monotonic per entity
- `content_hash` provides integrity verification and idempotency

---

## 1.1 - Minor

**Status:** Current

### Changes

- Added `redirects_to` field for redirect support
- Optional field: `null` for normal entities, entity ID for redirects
- Backward compatible with 1.0.0 schema

### Schema

```json
{
  "schema_version": "1.1.0",
  "revision_id": 1,
  "created_at": "2025-01-15T10:30:00Z",
  "created_by": "entity-api",
  "entity_type": "item",
  "content_hash": 1234567890123456789,
  "redirects_to": "Q42",
  "entity": {
    "id": "Q42",
    "type": "item",
    "labels": {},
    "descriptions": {},
    "aliases": {},
    "claims": {},
    "sitelinks": {}
  }
}
```

**Example - Redirect entity:**

```json
{
  "schema_version": "1.1.0",
  "revision_id": 12346,
  "created_at": "2025-01-15T11:00:00Z",
  "created_by": "entity-api",
  "entity_type": "item",
  "content_hash": 1234567890123456790,
  "redirects_to": "Q42",
  "entity": {
    "id": "Q59431323",
    "type": "item",
    "labels": {},  // Empty - no data for redirect entity
    "descriptions": {},  // Empty
    "aliases": {},  // Empty
    "claims": {},  // Empty - no statements
    "sitelinks": {}  // Empty - no sitelinks
  }
}
```

### Metadata Fields

All fields from 1.0.0 schema, plus:

- `redirects_to`: Optional string pointing to redirect target entity ID
  - `null` for normal entities
  - Entity ID (e.g., "Q42") for redirect entities

### Redirect Entity Structure

Redirect entities have minimal tombstone structure:

```json
{
  "id": "Q59431323",
  "type": "item",
  "labels": {},  // Empty - no data for redirect entity
  "descriptions": {},  // Empty
  "aliases": {},  // Empty
  "claims": {},  // Empty - no statements
  "sitelinks": {}  // Empty - no sitelinks
}
```

**Rationale:**
- Redirects point to target entity, no duplicate data needed
- `redirects_to` provides clear redirect target
- Redirects can be reverted: create new revision with `redirects_to: null` and full entity data
- Supports merge operations: source becomes redirect tombstone
- Backward compatible: readers ignore unknown fields, 1.0.0 readers work

### Impact

- Readers: Must handle redirect entities (empty content, redirects_to field)
- Writers: Entity API can create redirects via redirect tombstone revision
- Migration: Forward compatible (no data loss), requires populating redirects_to for new redirect revisions
- Vitess: New `entity_redirects` table provides fast lookup for RDF builder
- RDF Builder: Query Vitess for redirect information instead of MediaWiki API

### Notes

- Redirects follow immutable pattern: create new revision to revert
- Redirect entity IDs remain valid external identifiers
- S3 stores full revision history including redirect tombstones
- Vitess `entity_redirects` table provides O(log n) redirect lookups
- `redirects_to` in entity_head enables quick redirect status check
