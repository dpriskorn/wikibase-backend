# Conceptual Model

## Entity

An entity is a logical identifier only.

- `entity_id` (e.g. Q123)
- `entity_type` (item, property, lexeme, …)

Entities have no intrinsic state outside revisions.

An entity is a stable identifier only.

- `entity_id` (e.g. Q123)
- `entity_type` (item, property, lexeme, …)

Entities have no intrinsic state outside revisions.

---

## Revision

A revision is a complete, immutable snapshot of an entity.

- `entity_id`
- `revision_id` (monotonic per entity or content-hash based)
- `created_at`
- `snapshot_uri` (S3 object path)

Example:

s3://wikibase-revisions/Q123/r0000000042.json

Snapshot properties:
- Full canonical JSON
- Deterministic ordering
- Schema version embedded
- Written once, never modified


A revision is a complete snapshot of an entity.

- `entity_id`
- `revision_id` (monotonic per entity)
- `created_at`
- `snapshot_uri` (S3)
- `schema_version`
- `content_hash`


---
