# S3 Entity JSON Schema Changes

This document tracks all S3 entity JSON schema version changes for Wikibase immutable revision system.

## Quick Reference

| Version | Date | Type | Status |
|---------|------|------|--------|
| 1.0 | 2025-12-28 | Major | Current |

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
