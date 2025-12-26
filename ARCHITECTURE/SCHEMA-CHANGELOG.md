# Schema Changes

This document tracks all schema version changes for Wikibase immutable revision system.

## Quick Reference

| Version | Date | Type | Status |
|---------|------|------|--------|
| 1.0 | TBD | Major | Draft |

---

## 1.0 - Major

**Status:** Draft

### Changes

#### New Tables

**entity_id_mapping**

```sql
CREATE TABLE entity_id_mapping (
  internal_id BIGINT UNSIGNED NOT NULL,
  external_id VARCHAR(20) NOT NULL,
  entity_type ENUM('item', 'property', 'lexeme') NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (internal_id),
  UNIQUE KEY idx_external_id (external_id),
  KEY idx_external_type (external_id, entity_type),
  KEY idx_created_at (created_at)
) ENGINE=InnoDB;
```

**Purpose:** Single source of truth for internal (ulid-flake) ↔ external (Q123) ID translation

#### Modified Tables

**entity_head**

```sql
ALTER TABLE entity_head
  DROP COLUMN entity_id,
  ADD COLUMN internal_id BIGINT UNSIGNED NOT NULL,
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (internal_id),
  ADD INDEX idx_external_lookup (internal_id),
  ADD FOREIGN KEY (internal_id) REFERENCES entity_id_mapping(internal_id);
```

**entity_revisions**

```sql
ALTER TABLE entity_revisions
  DROP COLUMN entity_id,
  ADD COLUMN internal_id BIGINT UNSIGNED NOT NULL,
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (internal_id, revision_id),
  ADD FOREIGN KEY (internal_id) REFERENCES entity_id_mapping(internal_id);
```

**entity_revision_meta**

```sql
ALTER TABLE entity_revision_meta
  DROP COLUMN entity_id,
  ADD COLUMN internal_id BIGINT UNSIGNED NOT NULL,
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (internal_id, revision_id),
  ADD FOREIGN KEY (internal_id) REFERENCES entity_id_mapping(internal_id);
```

**entity_delete_audit**

```sql
ALTER TABLE entity_delete_audit
  DROP COLUMN entity_id,
  ADD COLUMN internal_id BIGINT UNSIGNED NOT NULL,
  ADD FOREIGN KEY (internal_id) REFERENCES entity_id_mapping(internal_id);
```

#### Schema Changes

**1. Entity ID Mapping Table**

- **Purpose:** Translation layer between internal ulid-flake and external Q123 IDs
- **Fields:**
  - `internal_id`: ulid-flake 64-bit (Vitess shard key, PRIMARY KEY)
  - `external_id`: Q123 format (UNIQUE index for lookups)
  - `entity_type`: item/property/lexeme (for filtering)
  - `created_at`, `updated_at`: Timestamps

**2. Updated Primary Keys**

All tables that previously used `entity_id` (Q123 format) now use `internal_id` (ulid-flake format):
- `entity_head.internal_id` (was `entity_id`)
- `entity_revisions.internal_id` (was `entity_id`)
- `entity_revision_meta.internal_id` (was `entity_id`)
- `entity_delete_audit.internal_id` (was `entity_id`)

**3. Foreign Key Constraints**

All modified tables reference `entity_id_mapping(internal_id)` for referential integrity

### Impact

#### Breaking Changes

**API Consumers:**
- **Entity creation requests**: Must now include `external_id` field (Q123/P42/L999)
- **Entity read requests**: No change (still use Q123/P42/L999)
- **SPARQL queries**: No change (still use Q123 in URIs)
- **RDF generation**: No change (still use Q123 in URIs)

**Database Consumers:**
- **Migration path**: Existing `entity_id` columns dropped, new `internal_id` columns added
- **Rollback plan**: Keep database backups before migration
- **Transition period**: Support both Q123 and hybrid lookups during migration

#### Non-Breaking Changes

**External ecosystem:**
- **SPARQL queries**: No changes required (still use Q123)
- **RDF dumps**: No changes required (still use Q123)
- **Public API endpoints**: No changes required (still use Q123)
- **S3 paths**: No changes required (still use Q123)

**Internal systems:**
- **Caching layer**: New `entity_id_mapping` cache required in Valkey/Redis
- **Identifier generation**: New ulid-flake generator service required
- **RDF generation**: Requires lookup from `entity_id_mapping` for external_id

### Migration Strategy

#### Phase 1: Schema Preparation (Week 1-2)
- Create `entity_id_mapping` table
- Add `internal_id` columns to all affected tables
- Create foreign key constraints
- Update Vitess VSchema

#### Phase 2: Initial Data Migration (Week 3-4)
- Populate `entity_id_mapping` for all existing entities:
  ```sql
  INSERT INTO entity_id_mapping (internal_id, external_id, entity_type, created_at)
  SELECT 
    ((UNIX_TIMESTAMP() * 1000) << 21) | 
    (ROW_NUMBER() OVER (ORDER BY entity_id) - 1) & 0x1FFFFF) as internal_id,
    entity_id as external_id,
    SUBSTRING(entity_id, 1, 1) as entity_type,
    NOW() as created_at
  FROM entity_head
  ORDER BY entity_id;
  ```
- Update all tables with new `internal_id` columns
- Drop old `entity_id` columns
- Verify data integrity

#### Phase 3: Service Deployment (Week 4-5)
- Deploy ulid-flake generator service
- Update API layer to use `entity_id_mapping` lookups
- Update RDF generation service
- Deploy caching layer (Valkey/Redis)
- Enable observability monitoring

#### Phase 4: Testing & Validation (Week 6)
- Unit tests for ulid-flake generation
- Integration tests for ID mapping
- Load tests for entity CRUD operations
- End-to-end tests: Create → Read → RDF → SPARQL
- Performance tests: Verify no regression

#### Phase 5: Production Rollout (Week 7-8)
- Deploy database schema changes
- Populate mapping table in production
- Rolling update of API services
- Monitor metrics for 24 hours
- Full production deployment

### Rollback Plan

If issues detected in production:
1. Restore database from pre-migration backup
2. Drop new `internal_id` columns from all tables
3. Restore `entity_id` columns to all tables
4. Drop `entity_id_mapping` table
5. Revert API services to previous versions
6. Revert RDF generation services

### Tags Field Use Cases

**For hybrid ID tracking:**
- Track migration batches: `["id-migration-v1.1", "batch-42"]`
- Mark entity types: `["item-type", "property-type", "lexeme-type"]`
- Audit ID changes: `["id-lookup", "id-generation"]`

### Notes

- **Identifier separation**: External IDs (Q123) are permanent for ecosystem compatibility; internal IDs (ulid-flake) are for database efficiency
- **No external changes**: SPARQL queries, RDF dumps, public APIs continue using Q123 without modification
- **Internal-only migration**: Only database schema and internal services change
- **Backward compatibility**: Support both Q123-only and hybrid lookups during transition period
- **Cache layer**: Critical performance optimization - cache `entity_id_mapping` lookups to avoid database queries
- **Vitess sharding**: `internal_id` (ulid-flake) provides uniform distribution, eliminates hot spots from Q123 sequential IDs
- **S3 paths**: Continue using external_id (Q123) for readability
- **ulid-flake format**: 64-bit with 42-bit timestamp + 21-bit randomness, no clock dependency
- **Identifier generation**: Distributed ulid-flake generator service creates IDs without coordination bottleneck

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
    "tags": ["import-2025", "batch-42", "invalid"]
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