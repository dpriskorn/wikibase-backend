# Schema Changes

This document tracks all schema version changes for the Wikibase immutable revision system.

## Quick Reference

| Version | Date | Type | Status |
|---------|------|------|--------|
| 1.0 | TBD | Major | Draft |

---

## 1.0 (TBD) - Major

**Status:** Draft

### Changes
- Initial schema definition
- Core entity model with required fields
- Optional `metadata.tags` array for classification and batch tracking

### Schema

```json
{
  "schema_version": "1.0",
  "entity": {
    "id": "string",
    "type": "item|property|lexeme",
    "labels": {},
    "descriptions": {},
    "aliases": {},
    "claims": {},
    "sitelinks": {}
  },
  "metadata": {
    "created_at": "ISO8601",
    "author_id": "string",
    "tags": ["import-2025", "batch-42"]
  }
}
```

### Impact
- Readers: Initial implementation
- Writers: Initial implementation
- Migration: N/A (baseline schema)

### Tags Field Use Cases
- Track import batches: `["import-2025", "batch-42"]`
- Classify entities: `["verified", "quality-check-passed"]`
- Audit trails: `["data-migration", "phase-2"]`

### Notes
- Establishes the canonical JSON format for immutable snapshots
- All fields required unless documented as optional
- Deterministic ordering enforced for hash stability
- `metadata.tags` is optional - tags are opaque strings with no enforced schema