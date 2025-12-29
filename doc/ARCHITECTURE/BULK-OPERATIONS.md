# Bulk Operations

## Bulk import

Write snapshots directly to S3

Batch-insert Vitess metadata

Publish events in bulk

Head pointers updated after batch completion

Designed for:
- Initial migration
- Large data ingests
- Backfills

---

## Bulk export

Stream snapshots from S3

Parallelized by entity_id

Deterministic ordering possible

No database pressure.
