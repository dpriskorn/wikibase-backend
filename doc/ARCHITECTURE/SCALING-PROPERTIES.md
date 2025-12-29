# Scaling Properties – Immutable Revision Wikibase Backend

This document explains why the immutable revision architecture
(S3 snapshots + Vitess indexing + API-first design)
scales to hundreds of millions or billions of entities without
hitting the structural limits of MediaWiki’s revision system.

---

## Fundamental scaling assumptions

The architecture is built on the following assumptions:

- Writes are frequent and continuous
- Reads are heavily skewed toward “latest state”
- History is important but rarely accessed
- Diffs are human-facing and infrequent
- Entities are independent and shardable

These assumptions match real-world Wikibase usage patterns.

---

## Write scalability

### Write cost per edit

Each edit performs a constant amount of work:

1. Validate entity JSON
2. Write one immutable snapshot to S3
3. Insert one lightweight metadata row in Vitess
4. Update one entity head pointer

There is:
- No global table
- No fan-out
- No cascading writes
- No synchronous secondary effects

**Write complexity:** `O(1)` per entity edit

---

### Absence of write amplification

Traditional MediaWiki writes trigger:

- Revision insert
- Text table insert
- RecentChanges insert
- Watchlist fan-out
- JobQueue scheduling
- Diff cache invalidation

In this architecture:

- One snapshot write
- One metadata insert
- One pointer update

This eliminates unbounded write amplification.

---

## Read scalability

### Hot-path reads (dominant case)

Most reads request the latest entity state.

```text
GET /entity/{id}
 → Vitess lookup (small, cacheable)
 → S3 fetch (CDN-backed)
