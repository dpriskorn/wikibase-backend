# Wikibase Backend

A clean-room, billion-scale Wikibase backend architecture based on immutable S3 snapshots and Vitess indexing.

## Core Principles

**The Immutable Revision Invariant:**

A revision is an immutable snapshot stored in S3. Once written, it never changes.

- No mutable revisions
- No diff storage
- No page-based state
- No MediaWiki-owned content

Everything else in the system derives from this rule.

## Architecture Overview

### Storage Stack
- **S3**: System of record storing all entity content as immutable snapshots
- **Vitess**: Index and metadata layer storing pointers to S3 objects

### Key Concepts
- **Entity**: A logical identifier (e.g., Q123) with no intrinsic state outside revisions
- **Revision**: Complete, immutable snapshot of an entity
- **Head Pointer**: Current revision pointer managed via compare-and-swap

## Getting Started

Start with [ARCHITECTURE.md](./ARCHITECTURE/ARCHITECTURE.md) for the complete architecture overview.

## Details
### Core

| Document                                                                          | Description                            |
|-----------------------------------------------------------------------------------|----------------------------------------|
| [ARCHITECTURE.md](./ARCHITECTURE/ARCHITECTURE.md)                                 | Main architecture overview             |
| [CONCEPTUAL-MODEL.md](./ARCHITECTURE/CONCEPTUAL-MODEL.md)                         | Conceptual model                       |
| [ENTITY-MODEL.md](./ARCHITECTURE/ENTITY-MODEL.md)                                 | Hybrid ID strategy (ulid-flake + Q123) |
| [STORAGE-ARCHITECTURE.md](./ARCHITECTURE/STORAGE-ARCHITECTURE.md)                 | S3 and Vitess storage design           |
| [CONSISTENCY-MODEL.md](./ARCHITECTURE/CONSISTENCY-MODEL.md)                       | Write atomicity and failure recovery   |
| [CONCURRENCY-CONTROL.md](./ARCHITECTURE/CONCURRENCY-CONTROL.md)                   | Optimistic concurrency with CAS        |
| [CACHING-STRATEGY.md](./ARCHITECTURE/CACHING-STRATEGY.md)                         | CDN and object cache design            |
| [CHANGE-NOTIFICATION.md](./ARCHITECTURE/CHANGE-NOTIFICATION.md)                   | Event streaming and consumers          |
| [S3-REVISION-SCHEMA-EVOLUTION.md](./ARCHITECTURE/S3-REVISION-SCHEMA-EVOLUTION.md) | Schema versioning and migration        |
| [S3-ENTITY-DELETION.md](./ARCHITECTURE/S3-ENTITY-DELETION.md)                     | Soft and hard delete semantics         |
| [BULK-OPERATIONS.md](./ARCHITECTURE/BULK-OPERATIONS.md)                           | Import and export operations           |

### Validation & Data Quality

| Document                                                                          | Description                                  |
|-----------------------------------------------------------------------------------|----------------------------------------------|
| [JSON-VALIDATION-STRATEGY.md](./ARCHITECTURE/JSON-VALIDATION-STRATEGY.md)         | API vs background validation trade-offs      |
| [POST-PROCESSING-VALIDATION.md](./ARCHITECTURE/POST-PROCESSING-VALIDATION.md)     | Background validation service implementation |
| [S3-REVISION-SCHEMA-CHANGELOG.md](./ARCHITECTURE/S3-REVISION-SCHEMA-CHANGELOG.md) | S3 JSONSchema version history                |

### RDF & Change Detection

| Document                                                                                              | Description                          |
|-------------------------------------------------------------------------------------------------------|--------------------------------------|
| [CHANGE-DETECTION-RDF-GENERATION.md](./ARCHITECTURE/CHANGE-DETECTION-RDF-GENERATION.md)               | RDF generation architecture overview |
| [JSON-RDF-CONVERTER.md](./ARCHITECTURE/JSON-RDF-CONVERTER.md)                                         | JSON→RDF conversion service          |
| [WEEKLY-RDF-DUMP-GENERATOR.md](./ARCHITECTURE/WEEKLY-RDF-DUMP-GENERATOR.md)                           | Weekly dump generation service       |
| [CONTINUOUS-RDF-CHANGE-STREAMER.md](./ARCHITECTURE/CONTINUOUS-RDF-CHANGE-STREAMER.md)                 | Real-time RDF streaming service      |
| [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](./ARCHITECTURE/MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md) | Change detection service             |
| [RDF-DIFF-STRATEGY.md](./ARCHITECTURE/RDF-DIFF-STRATEGY.md)                                           | RDF diff computation strategy        |

### Additional Resources

- [WIKIDATA-MIGRATION-STRATEGY.md](./WIKIDATA-MIGRATION-STRATEGY.md) - Migration from Wikidata
- [SCALING-PROPERTIES.md](./ARCHITECTURE/SCALING-PROPERTIES.md) - System scaling characteristics and bottlenecks
- [EXISTING-COMPONENTS/](./EXISTING-COMPONENTS/) - Documentation of existing MediaWiki/Wikidata components

### Design Philosophy

- **Immutability**: All content is stored as immutable snapshots
- **Eventual consistency**: With reconciliation guarantees and no data loss
- **Horizontal scalability**: S3 for storage, Vitess for indexing
- **Auditability**: Perfect revision history by design
- **Decoupling**: MediaWiki + Wikibase becomes a stateless API client

## External links
* https://www.mediawiki.org/wiki/User:So9q/Scaling_issues Implemenatation history and on-wiki details