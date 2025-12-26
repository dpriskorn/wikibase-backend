# Change Detection and RDF Generation Architecture

## Overview

This document describes services for generating RDF from entity snapshots and producing both continuous RDF change streams and weekly entity dumps (JSON + RDF formats).

Related documentation:
- [JSON-RDF-CONVERTER.md](./JSON-RDF-CONVERTER.md) - JSON→RDF converter service
- [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](./MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md) - Change detection service
- [WEEKLY-RDF-DUMP-GENERATOR.md](./WEEKLY-RDF-DUMP-GENERATOR.md) - Weekly RDF dump generator service
- [CONTINUOUS-RDF-CHANGE-STREAMER.md](./CONTINUOUS-RDF-CHANGE-STREAMER.md) - Continuous RDF change streamer

## Requirements

1. **Weekly Dumps**: Generate complete dumps of all recent entities in both JSON and RDF formats weekly
2. **Continuous Streaming**: Stream recent changes as RDF patches in real-time
3. **Architecture Alignment**: Integrate with existing S3 + Vitess storage model

---

## Service 1: JSON→RDF Converter

See [JSON-RDF-CONVERTER.md](./JSON-RDF-CONVERTER.md) for complete documentation.

**Purpose**: Convert Wikibase JSON snapshots to RDF (Turtle format) using streaming generation

**Key Features**:
- Streaming approach for memory efficiency (1M+ entities/week scale)
- Complete Wikibase RDF mapping rules implementation
- Parallel claim conversion for throughput
- Comprehensive error handling and validation
- Graph loading support for diff computation

**Technology Stack**:
- RDF libraries: rdflib (Python), RDF4J (Java), Apache Jena (Java)
- Streaming: Process large entities without full in-memory load

---

## Service 2: Weekly Dump Generator

See [WEEKLY-RDF-DUMP-GENERATOR.md](./WEEKLY-RDF-DUMP-GENERATOR.md) for complete documentation.

**Purpose**: Generate weekly dumps of all entities in both JSON and RDF formats as standalone S3 files

**Data Flow**:
```
Weekly Scheduler (Cron/Airflow)
          ↓
     Query entity_head: Get all entities
          ↓
     Batch fetch S3 snapshots (parallel, 1000s at a time)
          ↓
     ┌──────────────────────────────────┐
     ↓                              ↓
Convert to JSON Dump           Convert to RDF (Turtle) - Streaming
     ↓                              ↓
Write to S3:                     Write to S3:
  dump/YYYY-MM-DD/full.json       dump/YYYY-MM-DD/full.ttl
  (optional partitioned)          (optional partitioned)
```

**Key Features**:
- Scheduled weekly generation (configurable via Cron/Airflow)
- Both JSON and RDF (Turtle) format outputs
- Streaming generation for memory efficiency
- Automatic partitioning for large datasets
- Compression support (gzip)
- S3 lifecycle management and retention policies
- Comprehensive validation and checksums

---

## Complete Integrated Architecture

### Full Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Client API                                   │
│                           ↓                                       │
│                      Validate Entity                                 │
│                           ↓                                       │
│                   Assign Revision ID                                  │
│                           ↓                                       │
│                    Write S3 Snapshot                                │
│                           ↓                                       │
│                    Insert Vitess Metadata                             │
│                           ↓                                       │
│                  Emit MediaWiki Change Event (existing)              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ Change Detection Service
                                     │ (see MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RDF Generation Services                                         │
│                                                                  │
│                    Entity Changes (from Change Detection)               │
│                            ↓                                     │
│              ┌──────────────┴─────────────────────────┐                 │
│              ↓                                      │                  │
│    Continuous RDF Change Stream          Weekly RDF Dump Service    │
│         (Real-time)                        (Scheduled)                │
│              ↓                                      ↓                  │
│    JSON→RDF Converter              JSON→Turtle Dump Converter       │
│              ↓                                      ↓                  │
│    Compute RDF Diff                      Batch RDF Generation          │
│              ↓                                      ↓                  │
│    Emit rdf_change events              Write S3: full.ttl           │
│    (Kafka)                              (with metadata)               │
└─────────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Kafka Topic                                │
│                                                                  │
│  Topic: wikibase.rdf_change (reuse or new)                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Consumers                                      │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │   WDQS Consumer   │  │  Search Indexer    │                │
│  │ (reuse existing)  │  │   (optional)        │                │
│  │                   │  │                    │                │
│  │ - Apply patches    │  │ - Index from dump   │                │
│  │   to Blazegraph   │  │ - Stream updates    │                │
│  │                   │  │                    │                │
│  └──────────────────────┘  └──────────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Summary

| Component | Inputs | Outputs | Technology |
|-----------|---------|----------|------------|
| **Change Detection** | entity_head + entity_revisions + S3 snapshots | Entity change events | See MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md |
| **JSON→RDF Converter** | Entity JSON snapshots | RDF (Turtle format) | See JSON-RDF-CONVERTER.md |
| **Weekly RDF Dump Service** | entity_head + S3 snapshots (all recent entities) | S3: weekly JSON + RDF dump files | See WEEKLY-RDF-DUMP-GENERATOR.md |
| **Continuous RDF Change Streamer** | Entity change events | `rdf_change` events (Kafka) | See CONTINUOUS-RDF-CHANGE-STREAMER.md |
| **Existing WDQS Consumer** | `rdf_change` events (Kafka) | Apply patches to Blazegraph | Java (existing) |

---

## Implementation Phases

### Phase 1: Change Detection (2-3 weeks)
- See [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](./MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md) for implementation details
- Build Change Detector service
- Implement entity_head polling logic
- Add metrics and monitoring
- Deploy to staging

### Phase 2: RDF Conversion (2-3 weeks)
- See [JSON-RDF-CONVERTER.md](./JSON-RDF-CONVERTER.md) for complete documentation
- [ ] Test conversion fidelity with Wikidata examples
- [ ] Build RDF diff computation (using Jena/RDF4J) - see [RDF-DIFF-STRATEGY.md](./RDF-DIFF-STRATEGY.md)
- [ ] Validate RDF output against Blazegraph

### Phase 3: Weekly Dumps (2-3 weeks)
- See [WEEKLY-RDF-DUMP-GENERATOR.md](./WEEKLY-RDF-DUMP-GENERATOR.md) for complete documentation
- Deploy to production and set up cron schedule

### Phase 4: Continuous RDF Streaming (2 weeks)
- See [CONTINUOUS-RDF-CHANGE-STREAMER.md](./CONTINUOUS-RDF-CHANGE-STREAMER.md) for complete documentation
- Deploy to production and integrate with Change Detection service

### Phase 5: Integration & Testing (2 weeks)
- [ ] Integrate all components
- [ ] End-to-end testing with sample entities
- [ ] Performance testing (latency, throughput)
- [ ] Deploy to production
- [ ] Set up monitoring and alerting

---

## Advantages

| Benefit | Description |
|----------|-------------|
| **MediaWiki Independence** | See [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](./MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md) |
| **Backfill Capable** | Can process historical changes from any point in time |
| **Deterministic** | Based on immutable snapshots and ordered revision metadata |
| **Scalable** | All services can scale independently (S3, Vitess, Kafka) |
| **Dual Output** | Supports both continuous streaming (diffs) and batch dumps (full snapshots) |
| **Flexible** | Multiple consumers can use outputs (WDQS, search, analytics, mirrors) |

---

## Open Questions

1. **Change Granularity**: Entity-level diffs or claim-level diffs for RDF stream? entity-level diffs
2. **Snapshot Retention**: How long to keep weekly dumps in S3? Lifecycle rules? 1y rolling
3. **Performance Targets**: Latency targets for RDF conversion? Throughput requirements?
4. **Weekly Dump Partitioning**: Single file vs. multiple partitions at 1M entities/week scale? Multiple

---

## Architecture Notes

### MediaWiki Event Consumption

If MediaWiki EventBus continues emitting change events, the Continuous RDF Change Streamer can consume them directly:

```
MediaWiki Events → Fetch Entity from S3 → Convert to RDF → Emit rdf_change
```

This is documented in [CONTINUOUS-RDF-CHANGE-STREAMER.md](./CONTINUOUS-RDF-CHANGE-STREAMER.md) as an alternative input source.

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Core architecture principles
- [STORAGE-ARCHITECTURE.md](./STORAGE-ARCHITECTURE.md) - S3 + Vitess storage model
- [JSON-RDF-CONVERTER.md](./JSON-RDF-CONVERTER.md) - JSON→RDF converter service
- [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](./MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md) - Change detection service documentation
- [CONTINUOUS-RDF-CHANGE-STREAMER.md](./CONTINUOUS-RDF-CHANGE-STREAMER.md) - Continuous RDF change streamer service
- [WEEKLY-RDF-DUMP-GENERATOR.md](./WEEKLY-RDF-DUMP-GENERATOR.md) - Weekly RDF dump generator service
- [RDF-DIFF-STRATEGY.md](./RDF-DIFF-STRATEGY.md) - RDF diff strategy (Option A: Full Convert + Diff)
- [CHANGE-NOTIFICATION.md](./CHANGE-NOTIFICATION.md) - Existing event notification system
- [SCHEMAS-EVENT-PRIMARY-SUMMARY.md](../SCHEMAS-EVENT-PRIMARY-SUMMARY.md) - RDF change schema documentation
- [STREAMING-UPDATER-PRODUCER.md](../STREAMING-UPDATER-PRODUCER.md) - Existing MediaWiki→RDF pipeline
- [STREAMING-UPDATER-CONSUMER.md](../STREAMING-UPDATER-CONSUMER.md) - Existing RDF consumer for Blazegraph
