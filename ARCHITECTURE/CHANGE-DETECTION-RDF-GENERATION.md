# Change Detection and RDF Generation Architecture

## Overview

This document describes how to compute recent changes independently of MediaWiki and generate both continuous RDF change streams and weekly entity dumps (JSON + RDF formats) based on immutable S3 snapshots and Vitess metadata.

## Requirements

1. **MediaWiki-Independent Change Detection**: Compute recent entity changes without depending on MediaWiki EventBus
2. **Weekly Dumps**: Generate complete dumps of all recent entities in both JSON and RDF formats weekly
3. **Continuous Streaming**: Stream recent changes as RDF patches in real-time
4. **Architecture Alignment**: Integrate with existing S3 + Vitess storage model

---

## Current Architecture Dependencies

### Storage Infrastructure

| Component | Data Stored | Purpose |
|-----------|-------------|---------|
| **S3** | Immutable revision snapshots (full entity JSON) | System of record for all entity content |
| **Vitess** | Metadata only (`entity_head`, `entity_revisions`) | Pointers to S3, revision history, deletion audit |

### Existing Data Flow

```
Client API → Validate → Assign revision_id → S3 snapshot → Vitess metadata → MediaWiki event
```

### Limitation

- **MediaWiki Dependency**: Change events only emitted by MediaWiki EventBus
- **No Change History in Storage**: Vitess stores revision metadata, but no computed changes
- **Backfill Impossible**: Cannot compute historical changes without MediaWiki events

---

## Solution: MediaWiki-Independent Change Detection

### Core Principle

**Poll entity_head and fetch previous revision from entity_revisions, compare snapshots**

Since S3 stores complete entity snapshots and Vitess provides ordered revision metadata, we can compute changes by:
1. Polling entity_head for recently updated entities
2. Querying entity_revisions for the previous revision
3. Fetching both snapshots from S3
4. Computing JSON diffs between snapshots
5. Emitting rdf_change events directly

**Design Decision**: No new tables required. Uses existing `entity_head` and `entity_revisions` tables only.

### Implementation Design

#### Service 1: Snapshot Change Detector

**Purpose**: Poll Vitess and compute recent entity changes using existing S3 snapshots

**Data Flow**:
```
                  Vitess (existing tables)
                            ↓
                Poll entity_head (recent updates)
                            ↓
                      Query entity_revisions for previous revision
                            ↓
                      Fetch both S3 snapshots
                            ↓
                      Compute JSON Diff
                            ↓
                      Emit json_change events
```

**Algorithm** (S3-based approach):
```
1. Poll entity_head for recently updated entities:
   SELECT entity_id, head_revision_id, updated_at
   FROM entity_head
   WHERE updated_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
   ORDER BY updated_at ASC
   LIMIT 100000;

2. For each changed entity:
   a. Get current revision snapshot URI from entity_head
      current_rev_id = head_revision_id
      current_snapshot = s3.fetch(snapshot_uri)

   b. Query entity_revisions for previous revision:
      SELECT revision_id, snapshot_uri
      FROM entity_revisions
      WHERE entity_id = ? AND revision_id < ?
      ORDER BY revision_id DESC
      LIMIT 1

   c. Fetch previous revision snapshot:
      if previous_revision exists:
         prev_snapshot = s3.fetch(previous_snapshot_uri)

   d. Compute JSON diff between snapshots:
      Use library: google-diff-match-patch, jsondiffpatch, or custom

   e. Emit json_change event if diff detected
```

**Alternative Algorithm** (MediaWiki event-based - simpler):
```
1. Consume MediaWiki change events (from existing EventBus)
2. Extract entity_id and revision_id from event
3. Fetch S3 snapshot for that revision: s3.fetch(f"bucket/{entity_id}/r{rev_id}.json")
4. Convert snapshot JSON to RDF (Turtle format)
5. Emit rdf_change event with operation: import (for new entity) or diff (if tracking previous state)
```

**Recommendation**: Start with MediaWiki event-based approach if MediaWiki is available and emitting events. Use S3-based approach only if you need MediaWiki independence.

**Key Design Decisions**:
- **No new tables needed**: Uses existing `entity_head` and `entity_revisions`
- **No change history stored**: Just query for recent updates and previous revision
- **Simple checkpointing**: `entity_head.head_revision_id` is always the latest state

**Event Schema** (optional, for internal use):
```yaml
# Internal event for JSON→RDF conversion pipeline
# May be optional if direct pipeline from change detection to RDF
entity_id: string
from_revision_id: integer
to_revision_id: integer
json_diff: array  # JSON patch operations
```

**Technology Stack**:
- Language: Python, Scala, or Go
- Libraries:
  - Vitess client: `go-vitess`, `vtgate-client`, or SQL proxy
  - S3 client: AWS SDK, MinIO client
  - Diff library: `google-diff-match-patch`, `jsondiffpatch`
  - Kafka producer: `confluent-kafka`, `sarama`

**Configuration**:
| Option | Description | Default |
|---------|-------------|---------|
| `vitess_host` | Vitess VTGate host | localhost:15991 |
| `s3_bucket` | S3 bucket for snapshots | wikibase-revisions |
| `poll_interval` | How often to poll entity_head for changes | 300s (5 minutes) |
| `batch_size` | Entities to process in parallel | 1000 |
| `kafka_topic` | Topic to emit RDF changes | wikibase.rdf_change |
| `change_detection_enabled` | Enable/disable change detection | true |
| `use_mediawiki_events` | Consume MediaWiki events directly | false |

---

### Service 2: JSON→RDF Converter

**Purpose**: Convert Wikibase JSON snapshots to RDF (Turtle format) using streaming generation

**Conversion Mapping** (based on Wikibase RDF mapping rules):

| JSON Field | RDF Triple Pattern |
|-----------|------------------|
| Entity ID | `<entity_uri> a wikibase:Item .` |
| Labels | `<entity_uri> rdfs:label "label"@lang .` |
| Descriptions | `<entity_uri> schema:description "description"@lang .` |
| Aliases | `<entity_uri> skos:altLabel "alias"@lang .` |
| Claims | `<entity_uri> p:P<property> [statement] .` |
| Sitelinks | `<entity_uri> schema:sameAs <wiki_url> .` |

**Implementation - Streaming Approach** (critical for 1M+ entities/week scale):

```python
def json_stream_to_rdf_turtle(json_input: io.TextIO, ttl_output: io.TextIO):
    """Stream JSON to RDF without loading full entity in memory"""
    
    # Write Turtle header once
    ttl_output.write("""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix p: <http://www.wikidata.org/prop/direct/> .

""")
    
    # Stream entities line-by-line
    for line in json_input:
        entity = json.loads(line)
        entity_uri = f"http://www.wikidata.org/entity/{entity['id']}"
        
        # Write entity triples immediately (don't build full string)
        ttl_output.write(f"\n# Entity: {entity_uri}\n")
        ttl_output.write(f"<{entity_uri}> a wikibase:Item .\n")
        
        # Stream labels
        for lang, label in entity.get('labels', {}).items():
            ttl_output.write(f'<{entity_uri}> rdfs:label "{escape_turtle(label)}"@{lang} .\n')
        
        # Stream claims (claim-by-claim, not all at once)
        for prop_id, claims in entity.get('claims', {}).items():
            for claim in claims:
                statement_uri = generate_statement_uri(claim['id'])
                ttl_output.write(f'<{entity_uri}> p:{prop_id} {statement_uri} .\n')
                ttl_output.write(f'{statement_uri} a wikibase:Statement .\n')
                
                # Write claim values immediately
                write_statement_values(ttl_output, statement_uri, claim)
        
        ttl_output.write(f"\n# --- End entity: {entity_uri} ---\n\n")
        
        # Flush periodically (every 1000 triples)
        if ttl_output.triple_count % 1000 == 0:
            ttl_output.flush()
```

**Optimizations** (for scale):
1. **Caching**: Cache frequent RDF prefixes and templates
   ```python
   TURTLE_PREFIXES = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix p: <http://www.wikidata.org/prop/direct/> .
"""
   
   CLAIM_TEMPLATE = """{entity_uri} p:{prop_id} {statement_uri} .
{statement_uri} a wikibase:Statement .
"""   ```

2. **Parallel Claim Conversion** (one thread per property group):
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   def process_property_group(entity, property_ids):
       for prop_id in property_ids:
           claims = entity['claims'].get(prop_id, [])
           for claim in claims:
               write_claim_triples(ttl_output, claim)
   
   # Group properties by claim count (light vs heavy entities)
   executor = ThreadPoolExecutor(max_workers=10)
   executor.map(lambda props: process_property_group(entity, props), property_groups)
   ```

3. **Streaming Turtle Generation**: Write line-by-line, never build full document in memory
   - Avoid OOM on entities with 1000+ claims
   - Flush output buffer periodically (every 1000 triples)

**Technology Stack**:
- RDF libraries: rdflib (Python), RDF4J (Java), Apache Jena (Java)
- Template engine: Jinja2, Mustache for Turtle templates
- Streaming: Process large entities without full in-memory load

---

### Service 3: Weekly Dump Generator

**Purpose**: Generate weekly dumps of all entities in both JSON and RDF formats as standalone S3 files

**Critical Design Decision**: Weekly dumps are FILES, not Kafka events. The `rdf_change` schema is NOT used for weekly dumps - use standard Turtle format directly.

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

**Critical Design Decision**: Weekly dumps are FILES, not Kafka events. The `rdf_change` schema is NOT used for weekly dumps - use standard Turtle format directly.

**Implementation Design**:

#### Step 1: Query Changed Entities
```sql
SELECT DISTINCT h.entity_id, h.head_revision_id, h.updated_at
FROM entity_head h
WHERE h.updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY h.updated_at ASC;
```

#### Step 2: Batch Fetch S3 Snapshots
```python
def fetch_snapshots_in_batches(entity_ids: List[str], batch_size: int = 1000):
    """Fetch S3 snapshots in parallel batches"""
    for batch_start in range(0, len(entity_ids), batch_size):
        batch = entity_ids[batch_start:batch_start + batch_size]

        # Build S3 URIs
        uris = [
            f"s3://bucket/{entity_id}/r{revision_id}.json"
            for entity_id, revision_id in batch
        ]

        # Fetch in parallel
        snapshots = s3_client.get_objects(uris)

        # Process batch
        yield snapshots
```

#### Step 3: Generate Outputs

**JSON Dump Format**:
```json
{
  "dump_metadata": {
    "generated_at": "2025-01-15T00:00:00Z",
    "time_range": "2025-01-08T00:00:00Z/2025-01-15T00:00:00Z",
    "entity_count": 1234567,
    "format": "canonical-json"
  },
  "entities": [
    {
      "entity": { ...full entity JSON... },
      "metadata": {
        "revision_id": 327,
        "entity_id": "Q42",
        "s3_uri": "s3://bucket/Q42/r327.json"
      }
    },
    ...
  ]
}
```

**RDF Dump Format** (Turtle):
```turtle
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix p: <http://www.wikidata.org/prop/direct/> .

# Dump metadata
[] a schema:DataDownload ;
    schema:dateModified "2025-01-15T00:00:00Z"^^xsd:dateTime ;
    schema:temporalCoverage "2025-01-08T00:00:00Z/2025-01-15T00:00:00Z" ;
    schema:numberOfItems 1234567 ;
    dcat:downloadURL <https://s3.amazonaws.com/bucket/dump/2025-01-15/full.ttl> .

# Entity Q42
wd:Q42 a wikibase:Item ;
    rdfs:label "Douglas Adams"@en ;
    rdfs:label "Douglas Adams"@de ;
    schema:description "English writer and humorist"@en ;
    ...

# Entity Q123
wd:Q123 a wikibase:Item ;
    ...
```

**S3 Output Structure**:
```
s3://wikibase-dumps/
  weekly/
    2025/
      01/
        15/
          full.json              # Complete JSON dump
          full.ttl               # Complete RDF (Turtle) dump
          part-00001.ttl         # Optional split for large datasets
          part-00002.ttl
          ...
          metadata.json          # Dump metadata with generation info
          manifest.txt            # Optional checksums for validation
```

**Configuration**:
| Option | Description | Default |
|---------|-------------|---------|
| `schedule` | Cron expression for weekly dumps | `0 2 * * 0` (Sunday 2AM) |
| `s3_dump_bucket` | S3 bucket for dumps | wikibase-dumps |
| `batch_size` | Entities per batch | 1000 |
| `parallel_workers` | Parallel conversion threads | 10 |
| `format_versions` | JSON and RDF formats to generate | `["canonical-1.0", "turtle-1.1"]` |
| `compression` | Output compression | `gzip` |

---

### Service 4: Continuous RDF Change Streamer

**Purpose**: Convert JSON changes to RDF patches and stream continuously

**Architecture**:
```
Snapshot Change Detector Service
           ↓ (json_change events)
      JSON→RDF Converter
           ↓
     Compute RDF Diff (between two RDF representations)
           ↓
      Emit rdf_change events (Kafka)
           ↓
  WDQS Consumer / Other Consumers
           ↓
       Apply patches to Blazegraph
```

**Reuse Existing Schema** (`rdf_change/2.0.0`):
```yaml
# Continuous change event
$schema: /mediawiki/wikibase/entity/rdf_change/2.0.0
entity_id: "Q42"
operation: "diff"  # or "import" for weekly dumps
rev_id: 327
sequence: 0
sequence_length: 1
rdf_added_data:
  data: |
    <http://www.wikidata.org/entity/Q42> rdfs:label "New Label"@en .
    <http://www.wikidata.org/entity/Q42> p:P31 <http://www.wikidata.org/entity/Q5> .
  mime_type: text/turtle
rdf_deleted_data:
  data: |
    <http://www.wikidata.org/entity/Q42> rdfs:label "Old Label"@en .
    <http://www.wikidata.org/entity/Q42> p:P31 <http://www.wikidata.org/entity/Q123> .
  mime_type: text/turtle
```

**Weekly Dump as rdf_change** (operation: import):
```yaml
# Weekly dump can emit import events for each entity
entity_id: "Q42"
operation: "import"
rev_id: 327
rdf_added_data:
  data: |
    <http://www.wikidata.org/entity/Q42> a wikibase:Item ;
      rdfs:label "Label"@en ;
      schema:description "Description"@en ;
      p:P31 <http://www.wikidata.org/entity/Q5> ;
      p:P569 "1952-03-11"^^xsd:date .
  mime_type: text/turtle
# No rdf_deleted_data for import
```

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
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  [NEW] Change Detection + RDF Generation Service                 │
│                                                                  │
│                    Poll entity_head (recent updates)                     │
│                            ↓                                     │
│              Query entity_revisions for previous revision                   │
│                            ↓                                     │
│                    Fetch S3 snapshots (current + previous)                │
│                            ↓                                     │
│              ┌──────────────┴─────────────────────────┐                 │
│              ↓                                      │                  │
│         Compute JSON Diff                          Convert to RDF (Turtle)    │
│              ↓                                      │                  │
│         Emit rdf_change events (Kafka)              Compute RDF diff          │
│              ↓                                      │                  │
│                                                         │            │
│                                                         ↓            │
│                                      Emit rdf_change events (diff or import)│
└─────────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Weekly RDF Dump Service                                  │
│                                                                  │
│  Trigger: Weekly Cron                                             │
│                     ↓                                            │
│         Query entity_head (all entities)                             │
│                     ↓                                            │
│         Batch fetch S3 snapshots                                      │
│                     ↓                                            │
│              ┌──────────────────────────────────────┐                  │
│              ↓                                      │                  │
│         JSON Dump                          RDF (Turtle) Dump      │
│              ↓                                      │                  │
│         Write S3: full.json                  Write S3: full.ttl │
│                                                         │            │
│              (with metadata)                     (with metadata)    │
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
| **Change Detection + RDF Generation** | entity_head + entity_revisions + S3 snapshots | `rdf_change` events (Kafka) | Python/Scala/Go |
| **Weekly RDF Dump Service** | entity_head + S3 snapshots (all recent entities) | S3: weekly JSON + RDF dump files | Python/Scala |
| **Existing WDQS Consumer** | `rdf_change` events (Kafka) | Apply patches to Blazegraph | Java (existing) |

---

## Implementation Phases

### Phase 1: Foundation (1-2 weeks)
- [ ] Implement S3 snapshot fetcher (use existing S3 URIs from Vitess)
- [ ] Create JSON diff library wrapper
- [ ] Set up Kafka topics for `rdf_change` events
- [ ] Implement `entity_head` polling logic

### Phase 2: Change Detection (2-3 weeks)
- [ ] Build Snapshot Change Detector service
- [ ] Implement entity_head polling logic
- [ ] Add metrics and monitoring
- [ ] Deploy to staging

### Phase 3: RDF Conversion (2-3 weeks)
- [ ] Implement JSON→Turtle converter
- [ ] Test conversion fidelity with Wikidata examples
- [ ] Build RDF diff computation (using Jena/RDF4J)
- [ ] Validate RDF output against Blazegraph

### Phase 4: Weekly Dumps (2-3 weeks)
- [ ] Implement batch fetch logic
- [ ] Build JSON dump formatter
- [ ] Build RDF dump formatter
- [ ] Add compression and S3 upload
- [ ] Set up weekly cron schedule
- [ ] Implement manifest and checksum generation

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
| **MediaWiki Independence** | Compute changes directly from S3+Vitess, no MediaWiki API dependency |
| **Backfill Capable** | Can process historical changes from any point in time |
| **Deterministic** | Based on immutable snapshots and ordered revision metadata |
| **Scalable** | All services can scale independently (S3, Vitess, Kafka) |
| **Dual Output** | Supports both continuous streaming (diffs) and batch dumps (full snapshots) |
| **Flexible** | Multiple consumers can use outputs (WDQS, search, analytics, mirrors) |

---

## Open Questions

1. **Change Granularity**: Entity-level diffs or claim-level diffs for RDF stream?
2. **Backfill Strategy**: Should we process historical changes (from existing revisions) on initial deployment? No
3. **Snapshot Retention**: How long to keep weekly dumps in S3? Lifecycle rules? 1y rolling
4. **Performance Targets**: Latency targets for change detection? What's acceptable polling interval?
5. **Weekly Dump Partitioning**: Single file vs. multiple partitions at 1M entities/week scale? Multiple
6. **Consumer Coordination**: Should we use existing MediaWiki events or S3-based change detection (or both)? existing if possible at first
7. **RDF Change Strategy**: Use Option A (Full RDF Convert + Diff) at Scale

**Recommendation**: Full convert both snapshots to RDF and compute diff using proven RDF libraries (Jena, RDF4J)

**Rationale over Option B (JSON→RDF operation mapping)**:
- **Extremely error-prone** at Wikibase scale - entities have complex nested structures (claims, qualifiers, references)
- **Edge cases are hard** - claim removal affects references, qualifier changes affect multiple triples
- **No efficiency gain** - With streaming RDF conversion (line-by-line), you're reading full JSON anyway to generate complete RDF
- **Mapping bugs corrupt data** - If you miss converting a dependent triple, downstream consumers get inconsistent state

**Why Option A works better at scale**:
1. **Simpler implementation** - Use proven RDF diff libraries (Jena RDF Patch, RDF4J)
2. **Better reliability** - Correctness is more important than efficiency when dealing with 1B+ entities
3. **Easier iteration** - Easier to debug and extend
4. **Streaming approach mitigates memory** - Convert both revisions to RDF with streaming (line-by-line), then diff using memory-efficient algorithms

**Optimized flow**:
```
1. Stream from_snapshot JSON → RDF (Turtle, line-by-line)
2. Stream to_snapshot JSON → RDF (Turtle, line-by-line)
3. Load both RDF into in-memory graph structures
4. Compute RDF diff using proven library
5. Emit rdf_change event with added/deleted triples
```

**Hybrid optimization for very large entities**: If an entity has > 10K triples:
- Consider emitting `operation: import` for the new revision instead of `diff`
- Let consumer handle full replacement (effectively a full re-convert)
- This bypasses diff computation for the heaviest entities while still providing correct state 

---

## Architecture Notes

### Consume MediaWiki Events

If MediaWiki EventBus continues emitting change events, the simplest approach is:

```
MediaWiki Events → Fetch Entity from S3 → Convert to RDF → Emit rdf_change
```

This requires no change detection at all - just convert MediaWiki events to RDF format.

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Core architecture principles
- [STORAGE-ARCHITECTURE.md](./STORAGE-ARCHITECTURE.md) - S3 + Vitess storage model
- [CHANGE-NOTIFICATION.md](./CHANGE-NOTIFICATION.md) - Existing event notification system
- [SCHEMAS-EVENT-PRIMARY-SUMMARY.md](../SCHEMAS-EVENT-PRIMARY-SUMMARY.md) - RDF change schema documentation
- [STREAMING-UPDATER-PRODUCER.md](../STREAMING-UPDATER-PRODUCER.md) - Existing MediaWiki→RDF pipeline
- [STREAMING-UPDATER-CONSUMER.md](../STREAMING-UPDATER-CONSUMER.md) - Existing RDF consumer for Blazegraph
