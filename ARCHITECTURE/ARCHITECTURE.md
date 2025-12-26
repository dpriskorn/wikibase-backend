# Wikibase-backend
Immutable Revision Architecture (Vitess + S3)

This document describes a clean-room, billion-scale Wikibase backend
architecture based on immutable S3 snapshots, Vitess indexing, and a
well-defined API boundary. It incorporates design decisions, migration,
scaling properties, and revisions based on architectural review.

## Core invariant

**A revision is an immutable snapshot stored in S3.**  
Once written, it never changes.

There are:
- No mutable revisions
- No diff storage
- No page-based state
- No MediaWiki-owned content

Everything else in the system derives from this rule.

## Details

- [BULK-OPERATIONS.md](./BULK-OPERATIONS.md) - bulk operations
- [CACHING-STRATEGY.md](./CACHING-STRATEGY.md) - caching strategy and cost control
- [ENTITY-MODEL.md](./ENTITY-MODEL.md) - Hybrid ID strategy (ulid-flake + Q123)
- [SCHEMA-CHANGELOG.md](./SCHEMA-CHANGELOG.md) - S3 entity JSON schema changes
- [CHANGE-NOTIFICATION.md](./CHANGE-NOTIFICATION.md) - change notification and event streaming
- [CONCEPTUAL-MODEL.md](./CONCEPTUAL-MODEL.md) - conceptual model
- [CONCURRENCY-CONTROL.md](./CONCURRENCY-CONTROL.md) - concurrency control details
- [CONSISTENCY-MODEL.md](./CONSISTENCY-MODEL.md) - consistency model and failure recovery
- [ENTITY-DELETION.md](./ENTITY-DELETION.md) - entity deletion
- [REVISION-ID-STRATEGY.md](./REVISION-ID-STRATEGY.md) - revision ID strategy
- [SCHEMA-CHANGES.md](./SCHEMA-CHANGES.md) - schema change history and migration guides
- [SCHEMA-EVOLUTION.md](./SCHEMA-EVOLUTION.md) - schema evolution and migration
- [STORAGE-ARCHITECTURE.md](./STORAGE-ARCHITECTURE.md) - storage architecture

## S3 Entity JSON Schema Changes

### 1.1 - Hybrid Identifier Strategy (2025-01-26)

**Status:** Draft

**Description:** Add hybrid identifier strategy with internal ulid-flake and external Q123 IDs

**Changes:**

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

All modified tables reference `entity_id_mapping(internal_id)` for referential integrity.

### Impact

**Breaking Changes:**
- **API Consumers:**
  - Entity creation requests: Must now include `external_id` field (Q123/P42/L999)
  - Entity read requests: No change (still use Q123/P42/L999)

- **Database Consumers:**
  - Migration path: Existing `entity_id` columns dropped, new `internal_id` columns added
  - Rollback plan: Keep database backups before migration
  - Transition period: Support both Q123 and hybrid lookups during migration

**Non-Breaking Changes:**
- **External Ecosystem:**
  - SPARQL queries: No changes required (still use Q123 in URIs)
  - RDF dumps: No changes required (still use Q123 in URIs)
  - Public API endpoints: No changes required (still use Q123)
  - S3 paths: No changes required (still use Q123)

- **Internal Systems:**
  - Caching layer: New `entity_id_mapping` cache required in Valkey/Redis
  - Identifier generation: New ulid-flake generator service required
  - RDF generation: Requires lookup from `entity_id_mapping` for external_id

### Migration Strategy

**Phase 1: Schema Preparation (Week 1-2)**
- Create `entity_id_mapping` table
- Add `internal_id` columns to all affected tables
- Create foreign key constraints
- Update Vitess VSchema

**Phase 2: Initial Data Migration (Week 3-4)**
- Populate `entity_id_mapping` for all existing entities
- Update all tables with new `internal_id` columns
- Drop old `entity_id` columns
- Verify data integrity

**Phase 3: Service Deployment (Week 4-5)**
- Deploy ulid-flake generator service
- Update API layer to use `entity_id_mapping` lookups
- Update RDF generation service
- Deploy caching layer (Valkey/Redis)
- Enable observability monitoring

**Phase 4: Testing & Validation (Week 6)**
- Unit tests for ulid-flake generation
- Integration tests for ID mapping
- Load tests for entity CRUD operations
- End-to-end tests: Create → Read → RDF → SPARQL
- Performance tests: Verify no regression

**Phase 5: Production Rollout (Week 7-8)**
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
7. Clear all caches

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
