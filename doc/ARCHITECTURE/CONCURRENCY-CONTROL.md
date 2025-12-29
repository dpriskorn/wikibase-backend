# Concurrency Control

## Optimistic concurrency with CAS

Head updates use **compare-and-swap semantics**:

```sql
UPDATE entity_head
SET head_revision_id = :new
WHERE entity_id = :id
  AND head_revision_id = :expected
```

If the update fails:
- The client re-reads head
- Recomputes next revision
- Retries

This prevents:
- Head regression
- Lost updates
- Split-brain histories

---

## Write serialization scope

Concurrency is controlled per entity

No global locks

High-contention entities degrade locally only
