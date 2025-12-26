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
**See [CONCEPTUAL-MODEL.md](./CONCEPTUAL-MODEL.md) for the conceptual model.**

**See [STORAGE-ARCHITECTURE.md](./STORAGE-ARCHITECTURE.md) for the storage architecture.**

**See [CONCURRENCY-CONTROL.md](./CONCURRENCY-CONTROL.md) for concurrency control details.**

**See [CONSISTENCY-MODEL.md](./CONSISTENCY-MODEL.md) for consistency model and failure recovery.**

**See [REVISION-ID-STRATEGY.md](./REVISION-ID-STRATEGY.md) for the revision ID strategy.**

**See [CACHING-STRATEGY.md](./CACHING-STRATEGY.md) for caching strategy and cost control.**

**See [CHANGE-NOTIFICATION.md](./CHANGE-NOTIFICATION.md) for change notification and event streaming.**

**See [SCHEMA-EVOLUTION.md](./SCHEMA-EVOLUTION.md) for schema evolution strategy.**

**See [SCHEMA-CHANGES.md](./SCHEMA-CHANGES.md) for schema change history and migration guides.**

**See [ENTITY-DELETION.md](./ENTITY-DELETION.md) for entity deletion.**

**See [BULK-OPERATIONS.md](./BULK-OPERATIONS.md) for bulk operations.**
