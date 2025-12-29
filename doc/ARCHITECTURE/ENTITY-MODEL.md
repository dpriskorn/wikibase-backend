# Entity Model

## Entity

An entity is a logical identifier only.

- `entity_id` (e.g. Q123)
- `entity_type` (item, property, lexeme, …)

Entities have no intrinsic state outside revisions.

## External Entity Identifier

The **external entity ID** (e.g., `Q123`, `P42`, `L999`) is the permanent public-facing identifier used throughout the ecosystem:

- **API endpoints**: `/entity/Q123`, `/entity/Q123/revision/42`
- **SPARQL queries**: `SELECT ?item WHERE { ?item wdt:P31 wd:Q123 }`
- **RDF/JSON data**: Cross-entity references in claims use Q123
- **RDF triples**: `<http://www.wikidata.org/entity/Q42> a wikibase:Item`
- **RDF change events**: `entity_id: "Q42"` in event schemas
- **S3 paths**: Human-readable inspection (e.g., `s3://wikibase-revisions/Q123/r42.json`)

**Characteristics:**

- **Human-readable**: Easy to communicate and debug
- **Stable**: Never changes, permanent contract with external ecosystem
- **Compatible**: Works with all Wikidata tools, SPARQL queries, existing datasets
- **Semantic**: Prefix indicates entity type (Q=item, P=property, L=lexeme)

## Internal Entity Identifier

The **internal entity ID** is a 64-bit identifier used for database sharding and internal operations:

- **Format**: ulid-flake (64-bit ULID variant)
- **Purpose**: Efficient Vitess sharding and storage
- **Not exposed**: Never used in public APIs or user-facing systems

### ulid-flake Specification

**Binary layout:**

```
Bit 0:         1 bit   - Sign bit (always 0 for positive values)
Bits 1-42:      42 bits - Timestamp (milliseconds since Unix epoch)
Bits 43-63:     21 bits - Randomness (can embed shard identifier)
```

**Characteristics:**

| Feature | Value | Description |
|----------|---------|-------------|
| **Total size** | 64 bits | Perfect for Vitess BIGINT primary key |
| **Capacity** | ~2M IDs/ms | 2,097,152 possible values per timestamp |
| **Lifespan** | ~140 years | From Unix epoch (1970) until ~2110 |
| **Sortability** | ✓ Approximately time-ordered | Chronologically sortable within same millisecond |
| **Clock dependency** | None | Uses system timestamp directly |
| **Generation** | Distributed, no coordination | Each instance generates independently |
| **Collision resistance** | 21 bits of randomness | Negligible collision probability |

**Why ulid-flake over Snowflake:**

| Feature | Snowflake | ulid-flake | Winner |
|----------|-----------|--------------|---------|
| **64-bit size** | ✓ (8 bytes) | ✓ (8 bytes) | Tie |
| **Vitess compatibility** | ✓ (BIGINT) | ✓ (BIGINT) | Tie |
| **Library support** | ✓✓ Excellent | ✓ Good | Snowflake |
| **Throughput capacity** | 4K IDs/worker/ms | 2M IDs/ms | ulid-flake |
| **Clock dependency** | ✗ Problem (sequence counter) | ✓ No sequence counter | ulid-flake |
| **ID lifespan** | 69 years (custom epoch) | 140 years (Unix epoch) | ulid-flake |
| **Shard capacity** | 1024 workers | 2M values | ulid-flake |
| **Implementation complexity** | Medium (sequence management) | Simple (timestamp + randomness) | ulid-flake |

### Internal vs External ID Relationship

```
┌─────────────────────────────────────────────────────────┐
│              Internal Layer (Vitess)               │
│  ┌──────────────────────────────────────────────┐   │
│  │ entity_id_mapping                         │   │
│  │  ├─ internal_id (BIGINT PRIMARY KEY) │   │
│  │  ├─ external_id (Q123, UNIQUE)      │   │
│  │  └─ entity_type (item/property/lexeme) │   │
│  └──────────────────────────────────────────────┘   │
│                                                │
│  All other tables reference internal_id            │
│  (entity_head, entity_revisions, ...)            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│           External Layer (API, SPARQL, RDF)      │
│                                                │
│  Q123 used everywhere, never changes              │
│  - API: /entity/Q123                           │
│  - RDF: <http://www.wikidata.org/entity/Q123>   │
│  - SPARQL: SELECT ?item WHERE {?item wdt:P31 wd:Q123} │
│  - Events: entity_id: "Q123"                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  Translation Layer                │
│                                                │
│  entity_id_mapping provides:                   │
│  internal_id ↔ external_id lookup              │
│  Cached for performance (Redis/memcached)      │
└─────────────────────────────────────────────────────────┘
```

## Usage Examples

### Entity Creation

```
Client Request
POST /entities
{
  "external_id": "Q123",
  "entity_type": "item",
  "labels": {"en": {"language": "en", "value": "Douglas Adams"}},
  "claims": {...}
}
↓
API Layer
1. Validate external_id format (Q123, P42, L999)
2. Generate internal_id via ulid-flake service
3. Write S3 snapshot: s3://wikibase-revisions/Q123/r42.json
4. Insert entity_id_mapping: (internal_id=1424675744195114, external_id="Q123", entity_type="item")
5. Insert entity_head: (internal_id=1424675744195114, head_revision_id=42, updated_at=NOW())
6. Insert entity_revisions: (internal_id=1424675744195114, revision_id=42, created_at=NOW(), snapshot_uri="s3://...")
7. Emit change event: {external_id="Q123", revision_id=42, operation="diff"}
↓
Client Response
{
  "external_id": "Q123",     // Echo back
  "internal_id": 1424675744195114,
  "revision_id": 42,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Entity Read

```
Client Request
GET /entity/Q123
↓
API Layer
1. Query entity_id_mapping: 
   SELECT internal_id FROM entity_id_mapping WHERE external_id = "Q123"
2. Query entity_head: 
   SELECT head_revision_id, updated_at FROM entity_head WHERE internal_id = 1424675744195114
3. Fetch S3 snapshot: 
   GET s3://wikibase-revisions/Q123/r42.json
4. Attach external_id to response
↓
Client Response
{
  "external_id": "Q123",
  "internal_id": 1424675744195114,
  "entity": {...entity content...}
}
```

### RDF Generation

```
Change Detection Service
1. Poll entity_head: 
   SELECT internal_id, head_revision_id FROM entity_head WHERE updated_at >= %s
2. Query entity_id_mapping: 
   SELECT external_id FROM entity_id_mapping WHERE internal_id = 1424675744195114
3. Fetch S3 snapshot: GET s3://wikibase-revisions/Q123/r42.json
4. Generate RDF: 
   <http://www.wikidata.org/entity/Q123> a wikibase:Item .
   <http://www.wikidata.org/entity/Q123> rdfs:label "Douglas Adams"@en .
   <http://www.wikidata.org/entity/Q123> p:P31 <http://www.wikidata.org/entity/Q5> .
5. Emit event: 
   {
     "entity_id": "Q123",
     "operation": "diff",
     "rdf_added_data": {...Turtle format...}
   }
```

## Key Principles

1. **External ID stability**: Q123 never changes, maintains 100% ecosystem compatibility
2. **Internal ID efficiency**: ulid-flake provides uniform sharding distribution
3. **Mapping layer**: Single source of truth for internal ↔ external translation
4. **Zero disruption**: All SPARQL queries, RDF tools, public APIs continue working
5. **Separation of concerns**: External IDs for ecosystem, internal IDs for system efficiency

## Storage Example

```text
S3 Object Path:
  s3://wikibase-revisions/Q123/r42.json

Vitess Tables:
  entity_id_mapping:
    internal_id: 1424675744195114 (PRIMARY KEY)
    external_id: "Q123" (UNIQUE)
    entity_type: "item"
  
  entity_head:
    internal_id: 1424675744195114 (PRIMARY KEY)
    head_revision_id: 42
    updated_at: "2025-01-15T10:30:00Z"
```

## References

- [IDENTIFIER-STRATEGY.md](./IDENTIFIER-STRATEGY.md) - Complete hybrid ID strategy and implementation
- [STORAGE-ARCHITECTURE.md](STORAGE-ARCHITECTURE.md) - S3 and Vitess storage design
- [JSON-RDF-CONVERTER.md](JSON-RDF-CONVERTER.md) - RDF generation with external ID handling
