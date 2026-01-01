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

Start with [ARCHITECTURE.md](./doc/ARCHITECTURE/ARCHITECTURE.md) for the complete architecture overview.

## Details
### Core

| Document                                                                          | Description                            |
|-----------------------------------------------------------------------------------|----------------------------------------|
| [ARCHITECTURE.md](./doc/ARCHITECTURE/ARCHITECTURE.md)                                 | Main architecture overview             |
| [CONCEPTUAL-MODEL.md](./doc/ARCHITECTURE/CONCEPTUAL-MODEL.md)                         | Conceptual model                       |
| [ENTITY-MODEL.md](./doc/ARCHITECTURE/ENTITY-MODEL.md)                                 | Hybrid ID strategy (ulid-flake + Q123) |
| [STORAGE-ARCHITECTURE.md](./doc/ARCHITECTURE/STORAGE-ARCHITECTURE.md)                 | S3 and Vitess storage design           |
| [CONSISTENCY-MODEL.md](./doc/ARCHITECTURE/CONSISTENCY-MODEL.md)                       | Write atomicity and failure recovery   |
| [CONCURRENCY-CONTROL.md](./doc/ARCHITECTURE/CONCURRENCY-CONTROL.md)                   | Optimistic concurrency with CAS        |
| [CACHING-STRATEGY.md](./doc/ARCHITECTURE/CACHING-STRATEGY.md)                         | CDN and object cache design            |
| [CHANGE-NOTIFICATION.md](./doc/ARCHITECTURE/CHANGE-NOTIFICATION.md)                   | Event streaming and consumers          |
| [S3-REVISION-SCHEMA-EVOLUTION.md](./doc/ARCHITECTURE/S3-REVISION-SCHEMA-EVOLUTION.md) | Schema versioning and migration        |
| [S3-ENTITY-DELETION.md](./doc/ARCHITECTURE/S3-ENTITY-DELETION.md)                     | Soft and hard delete semantics         |
| [BULK-OPERATIONS.md](./doc/ARCHITECTURE/BULK-OPERATIONS.md)                           | Import and export operations           |

### Validation & Data Quality

| Document                                                                          | Description                                  |
|-----------------------------------------------------------------------------------|----------------------------------------------|
| [JSON-VALIDATION-STRATEGY.md](./doc/ARCHITECTURE/JSON-VALIDATION-STRATEGY.md)         | API vs background validation trade-offs      |
| [POST-PROCESSING-VALIDATION.md](./doc/ARCHITECTURE/POST-PROCESSING-VALIDATION.md)     | Background validation service implementation |
| [S3-REVISION-SCHEMA-CHANGELOG.md](./doc/ARCHITECTURE/S3-REVISION-SCHEMA-CHANGELOG.md) | S3 JSONSchema version history                |

### RDF & Change Detection

| Document                                                                                              | Description                          |
|-------------------------------------------------------------------------------------------------------|--------------------------------------|
| [RDF-BUILDER-IMPLEMENTATION.md](./doc/ARCHITECTURE/RDF-BUILDER-IMPLEMENTATION.md)                         | RDF builder implementation details |
| [CHANGE-DETECTION-RDF-GENERATION.md](./doc/ARCHITECTURE/CHANGE-DETECTION-RDF-GENERATION.md)               | RDF generation architecture overview |
| [JSON-RDF-CONVERTER.md](./doc/ARCHITECTURE/JSON-RDF-CONVERTER.md)                                         | JSON→RDF conversion service          |
| [WEEKLY-RDF-DUMP-GENERATOR.md](./doc/ARCHITECTURE/WEEKLY-RDF-DUMP-GENERATOR.md)                           | Weekly dump generation service       |
| [CONTINUOUS-RDF-CHANGE-STREAMER.md](./doc/ARCHITECTURE/CONTINUOUS-RDF-CHANGE-STREAMER.md)                 | Real-time RDF streaming service      |
| [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](./doc/ARCHITECTURE/MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md) | Change detection service             |
| [RDF-DIFF-STRATEGY.md](./doc/ARCHITECTURE/RDF-DIFF-STRATEGY.md)                                           | RDF diff computation strategy        |

### Additional Resources

- [WIKIDATA-MIGRATION-STRATEGY.md](./doc/WIKIDATA/WIKIDATA-MIGRATION-STRATEGY.md) - Migration from Wikidata
- [SCALING-PROPERTIES.md](./doc/ARCHITECTURE/SCALING-PROPERTIES.md) - System scaling characteristics and bottlenecks
- [EXISTING-COMPONENTS/](./doc/EXISTING-COMPONENTS/) - Documentation of existing MediaWiki/Wikidata components

### Design Philosophy

- **Immutability**: All content is stored as immutable snapshots
- **Eventual consistency**: With reconciliation guarantees and no data loss
- **Horizontal scalability**: S3 for storage, Vitess for indexing
- **Auditability**: Perfect revision history by design
- **Decoupling**: MediaWiki + Wikibase becomes a stateless API client

## RDF Testing Progress

### Test Entities

| Entity | Missing Blocks | Extra Blocks | Status |
|---------|----------------|----------------|---------|
| Q17948861 | 0 | 0 | ✅ Perfect match |
| Q120248304 | 0 | 2 | ✅ Perfect match (hash differences only) |
| Q1 | 44 | 35 | ✅ Excellent match (98.1%) |
| Q42 | 87 | 83 | 🟡 Good match (98.4%) |

### Implemented Fixes (Dec 2024)

**Phase 1: Datatype Mapping**
- Added `get_owl_type()` helper to map property datatypes to OWL types
- Non-item datatypes now generate `owl:DatatypeProperty` instead of `owl:ObjectProperty`

**Phase 2: Normalization Support**
- Added `psn:`, `pqn:`, `prn:`, `wdtn:` predicates for properties with normalization
- Added `wikibase:statementValueNormalized`, `wikibase:qualifierValueNormalized`, `wikibase:referenceValueNormalized`, `wikibase:directClaimNormalized` declarations
- Supports: time, quantity, external-id datatypes

**Phase 3: Property Metadata**
- Updated `PropertyShape` model to include normalized predicates
- Fixed blank node generation to use MD5 with proper repository name (`wikidata`)
- Fixed missing properties: Now collects properties from qualifiers and references, not just main statements

**Phase 4: Critical Bug Fixes (Dec 31)**
- **Fixed reference snaks iteration**: Changed `ref.snaks.values()` to `ref.snaks` (list, not dict)
- **Fixed URI formatting**: Removed angle brackets from prefixed URIs (`<wds:...>` → `wds:...`)
- **Fixed reference property shapes**: Each reference snak now uses its own property shape
- **Fixed time value formatting**: Strips "+" prefix to match Wikidata format
- **Fixed globe precision formatting**: Changed "1e-05" to "1.0E-5"
- **Fixed hash serialization**: Updated to include all fields (before/after for time, formatted precision for globe)
- **Fixed property declarations**: psv:, pqv:, prv: now declared for all properties
- **Fixed qualifier entity collection**: Entities referenced in qualifiers are now written to TTL
- **Downloaded missing metadata**: Fetched 59 entity metadata files from Wikidata SPARQL

**Phase 5: Data Model Alignment (Dec 31)**
- **Fixed globe precision format**: Implemented `_format_scientific_notation()` to remove leading zeros from exponents (e.g., "1.0E-05" → "1.0E-5")
- **Fixed time hash serialization**: Preserves "+" prefix in hash but omits before/after when 0 for consistency with Wikidata format
- **Fixed OWL property types**: psv:, pqv:, prv: are always owl:ObjectProperty; wdt: follows datatype (ObjectProperty for items, DatatypeProperty for literals)
- **Updated test expectations**: Aligned tests with golden TTL format from Wikidata

**Phase 6: Entity Metadata Fix (Jan 1)**
- **Fixed entity metadata download script**: Updated to collect referenced entities from qualifiers and references, not just mainsnaks
- **Fixed entity ID extraction**: Changed from `numeric-id` to `id` field for consistency with conversion logic
- **Downloaded 557 entity metadata files**: Fetched from Wikidata SPARQL endpoint to resolve all metadata warnings
- **Improved Q42 conversion**: Reduced missing blocks from 147 to 87 by adding 60 previously missing entity metadata files

**Test Status**
- ✅ Q17948861: Perfect match (0 missing, 0 extra)
- ✅ Q120248304: 0 missing, 2 extra (hash differences only - 100% content match)
- ✅ Q1: 44 missing, 35 extra (9 redirects + 35 value nodes)
- 🟡 Q42: 87 missing, 83 extra (98.4% match - complex entity with 293 properties)

**Integration Test Status**
- ✅ Property ontology tests (fixed OWL type declarations)
- ✅ Globe precision formatting (matches golden TTL: "1.0E-5")
- ✅ Time value serialization (preserves + prefix, omits before/after when 0)

**Remaining Issues**
- Redirect entities appear as "missing" but correctly use `owl:sameAs` (expected behavior)
- Value node hashes (different serialization algorithm - non-critical)
- Q42: 87 missing blocks remaining (mostly redirects and edge cases)

## External links
* https://www.mediawiki.org/wiki/User:So9q/Scaling_issues Implemenatation history and on-wiki details

## Code Quality

### Vulture (Dead Code Detection)

Run vulture to detect unused code:

```bash
source .venv/bin/activate
vulture src vulture_whitelist.txt
```

Or use the helper script:

```bash
./run_vulture.sh
```

The `vulture_whitelist.txt` file contains false positives that are not actually unused (e.g., FastAPI route functions, Pydantic model fields, etc.).
