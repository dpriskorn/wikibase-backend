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
- [ENTITY-MODEL.md](./ENTITY-MODEL.md) - Hybrid ID strategy (ulid-flake + Q123) |
- [CHANGE-NOTIFICATION.md](./CHANGE-NOTIFICATION.md) - change notification and event streaming
- [CONCEPTUAL-MODEL.md](./CONCEPTUAL-MODEL.md) - conceptual model
- [CONCURRENCY-CONTROL.md](./CONCURRENCY-CONTROL.md) - concurrency control details
- [CONSISTENCY-MODEL.md](./CONSISTENCY-MODEL.md) - consistency model and failure recovery
- [ENTITY-DELETION.md](./ENTITY-DELETION.md) - entity deletion

- [REVISION-ID-STRATEGY.md](./REVISION-ID-STRATEGY.md) - revision ID strategy
- [SCHEMA-CHANGES.md](./SCHEMA-CHANGES.md) - schema change history and migration guides
- [SCHEMA-EVOLUTION.md](./SCHEMA-EVOLUTION.md) - schema evolution and migration
- [STORAGE-ARCHITECTURE.md](./STORAGE-ARCHITECTURE.md) - storage architecture
