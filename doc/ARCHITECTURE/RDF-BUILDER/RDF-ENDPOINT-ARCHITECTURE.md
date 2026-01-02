# RDF Endpoint Architecture and Caching Strategy

## Overview

This document outlines the proposed architecture for a high-performance RDF endpoint that combines efficient caching with on-demand RDF generation, similar to MediaWiki Wikibase's approach.

## Problem Statement

Building RDF for complex entities (e.g., Q42) requires:
- Fetching multiple properties (293 for Q42)
- Fetching referenced entities (hundreds)
- Parsing entity data
- Constructing complex RDF graphs
- Serializing to Turtle format

**Result:** Response times that could be tens of seconds, which is not acceptable for an interactive API.

## Solution: Hybrid Caching + On-Demand RDF Generation

Instead of pre-generating and caching RDF dumps, we use a **24-hour cache for property types, item labels, and entity metadata**, combined with **on-demand RDF generation** for each request.

This approach:
- ✅ Reduces response time dramatically (seconds → milliseconds)
- ✅ Keeps data reasonably fresh (24h cache for metadata, live for RDF)
- ✅ Controls infrastructure costs (cache hits are cheap, database queries are minimized)
- ✅ Matches MediaWiki's approach (generate RDF on-demand, cache auxiliary data)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Client Request                   │
│                (GET /entity/Q123)              │
└──────────────────────┬──────────────────────────────┘
                     ↓
         ┌─────────────────────────────┐
         │ Browser/Client Cache        │
         │ (HTTP caching, ETags)       │
         └──────────┬────────────────────┘
                    ↓
            ┌────────────────────────┐
            │ CDN Cache (Optional) │
            │ 70-85% hit rate    │
            │ 1 year TTL            │
            │ S3 immutable snapshots  │
            └──────────┬─────────────┘
                       ↓
              (cache miss)
                 ↓
         ┌────────────────────────────────┐
         │ Application Object Cache     │
         │ Valkey / Memcached          │
         │ - entity_id_mapping         │
         │ - entity_head (NEW)        │
         │ - entity_metadata (NEW)     │
         │ TTL: 1 hour                │
         └──────────┬─────────────────────┘
                    ↓
         ┌────────────────────────────────┐
         │ Vitess Database             │
         │ - entity_id_mapping table     │
         │ - entity_head table (NEW)     │
         │ - entity_revisions table (NEW) │
         │ Query cache enabled              │
         └──────────┬─────────────────────┘
                    ↓
         (cache hit)
            ↓
         ┌────────────────────────────────┐
         │ RDF Builder                │
         │ (generate on-demand)           │
         └──────────┬─────────────────────┘
                    ↓
              Turtle RDF
                    ↓
         ┌────────────────────────────────┐
         │ S3 Object Store (NEW)       │
         │ Store for immutable snapshots   │
         └─────────────────────────────┘
                    ↓
            ┌────────────────────────────────┐
         │ API Response                │
         └─────────────────────────────┘
```

## Cache Layers (from CACHING-STRATEGY.md)

### Layer 1: Client Cache
- HTTP caching headers (ETag, Last-Modified)
- Cache-Control: public, max-age=3600
- Max-age directives
- Conditional requests (If-None-Match, If-Modified-Since)
- **Expected hit rate:** 40-60%
- **TTL:** 1 hour

### Layer 2: CDN Cache (Optional)
- S3 snapshots (immutable) for 1 year
- Cache-Control: public, max-age=31536000 (1 year)
- CDN CloudFront/Cloudflare edge caching
- S3 GET operations only
- **Expected hit rate:** 70-85% for hot entities
- **Use case:** Serve static content without application involvement

### Layer 3: Application Object Cache (Valkey/Memcached)

#### 3.1 Entity ID Mapping Cache (NEW for our use case)
**Purpose:** Fast lookup of external ID → internal UUID translation

**Cache key format:**
```
entity_id:{external_id}
```

**Examples:**
```
entity_id:Q123
entity_id:P42
entity_id:L999
```

**Cache value:**
```json
{
  "internal_id": 1424675744195114,
  "entity_type": "item",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**TTL:** 3600 seconds (1 hour)
- **Rationale:** External IDs never change, can cache indefinitely
- **Mappings rarely change:** Only if entity is deleted and recreated

#### 3.2 Entity Head Cache (NEW - Required for MediaWiki compatibility)
**Purpose:** Track current head revision pointer for entity

**Cache key format:**
```
entity_head:{internal_id}
```

**Cache value:**
```json
{
  "internal_id": 1424675744195114,
  "head_revision_id": 42,
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**TTL:** 300 seconds (5 minutes)
- **Rationale:** Head revisions update frequently on active entities
- **TTL fallback:** Ensures eventual consistency

#### 3.3 Entity Metadata Cache (NEW)
**Purpose:** Cache entity labels, descriptions, types for search/browse endpoints

**Cache key format:**
```
entity_meta:{internal_id}
```

**Cache value:**
```json
{
  "internal_id": 1424675744195114,
  "external_id": "Q123",
  "entity_type": "item",
  "labels": {
    "en": "Douglas Adams",
    "de": "Douglas Adams"
  },
  "descriptions": {
    "en": "English author"
  }
}
```

**TTL:** 1800 seconds (30 minutes)
- **Rationale:** Labels/descriptions change less frequently than entity data
- **Optimization:** Store in compressed format (gzip) to reduce memory

#### 3.4 Vitess Query Cache (NEW)
**Purpose:** Cache frequently executed SQL queries at database level

**Configuration:**
```sql
-- Enable Vitess query cache
SET GLOBAL query_cache_size = 256M;
SET GLOBAL query_cache_type = ON;

-- Cache common lookups
-- (entity_id_mapping queries, entity_head lookups)
```

**Expected hit rate:** 30-40% for repetitive queries
- **TTL:** Managed by Vitess (query plan cache)

### Layer 4: S3 Object Store (NEW)

**Purpose:** System of record for all entity snapshots

**Characteristics:**
- **Immutable:** Never modified after write
- **Cache-friendly:** CDN caches for 1 year
- **Global replication:** Multi-region S3 for low latency
- **No caching strategy needed:** Immutable by design

**Use case:**
- Store immutable entity snapshots (JSON)
- Serve via CDN with 1-year cache
- Reduce S3 GET operations

**Storage pattern:**
```
revisions/{external_id}/r{revision_id}.json
```

Examples:
```
revisions/Q123/r42.json
revisions/P42/r1.json
```

### Layer 5: Vitess Database Query

**Purpose:** Source of truth for entity data when caches miss

**Tables:**
- `entity_id_mapping` - External ID → internal ID translation
- `entity_head` - Current head revision pointer
- `entity_revisions` - Revision history (NEW)
- `entity_metadata` - Labels, descriptions (separate table or materialized view)

## Data Flow

### Request Flow (Cache Hit)

```
Client Request
  ↓
Browser Cache HIT
  ↓
CDN Cache HIT (if used)
  ↓
Application Cache HIT (entity_id_mapping)
  ↓
Lookup internal_id = 1424675744195114
  ↓
Query Vitess for entity data (using internal_id)
  ↓
RDF Builder generates Turtle RDF
  ↓
Return to client (latency: <100ms total)
```

### Request Flow (Cache Miss - New Entity)

```
Client Request
  ↓
Browser Cache MISS
  ↓
Application Cache MISS (entity_id_mapping)
  ↓
Query Vitess for entity ID mapping
  ↓
Insert new entity_id_mapping record (Q123 → 1424675744195114)
  ↓
Query Vitess for entity data (using internal_id)
  ↓
RDF Builder generates Turtle RDF
  ↓
Update Application Cache (entity_id_mapping)
  ↓
Return to client (latency: 200-500ms for database + RDF generation)
```

### Cache Invalidation

#### Immutable Data (Entity ID Mapping)
**Never invalidated** - External IDs never change

#### Mutable Data (Entity Head, Entity Metadata)
**Invalidated on:**
- Entity update (successful write)
- Revision creation
- Metadata change (label/description update)

**Strategy:**
```
def update_entity(entity_data: dict):
    external_id = entity_data['external_id']  # e.g., "Q123"
    internal_id = entity_data['internal_id']  # e.g., 1424675744195114

    # 1. Invalidate entity head cache
    entity_head_cache_key = f"entity_head:{internal_id}"
    valkey_client.delete(entity_head_cache_key)

    # 2. Invalidate entity metadata cache
    entity_meta_cache_key = f"entity_meta:{internal_id}"
    valkey_client.delete(entity_meta_cache_key)

    # 3. Write new S3 snapshot
    revision_id = get_next_revision_id()  # Generate new revision ID
    s3.put(f"revisions/{external_id}/r{revision_id}.json", entity_data)

    # 4. Update entity_head in Vitess
    db.update_entity_head(internal_id, revision_id)

    # 5. Update Application Cache
    cache_value = {
        "internal_id": internal_id,
        "head_revision_id": revision_id,
        "updated_at": str(datetime.now(timezone.utc))
    }
    cache_key = f"entity_head:{internal_id}"
    valkey_client.setex(cache_key, 3600, json.dumps(cache_value))  # 1 hour TTL

    return {"status": "success"}
```

## Performance Targets

### Expected Hit Rates (from CACHING-STRATEGY.md)

| Cache Layer | Expected Hit Rate | Target P50 Latency | Target P99 Latency |
|-------------|------------------|---------------------|---------------------|
| **Client cache** | 40-60% | 0ms (local) | 0ms (local) |
| **CDN cache** | 70-85% | 50ms | 200ms |
| **entity_id_mapping cache** | >95% | <1ms | <5ms |
| **entity_head cache** | 80-90% | <2ms | <10ms |
| **Entity metadata cache** | 70-80% | <5ms | <20ms |
| **Vitess query cache** | 30-40% | <10ms | <50ms |

### Full Request Latency (Warm Cache Path)

```
GET /entity/Q123 (hot entity, cached)
  ↓
Client cache HIT: <1ms
  ↓
App cache HIT (entity_id_mapping): <1ms
  ↓
Vitess cache HIT (entity data): <10ms
  ↓
RDF Builder (on-demand): 50-100ms
  ↓
Response time: 60-120ms (P50), 100-200ms (P99)
```

### Full Request Latency (Cold Cache Path)

```
GET /entity/Q123 (cold entity)
  ↓
Client cache MISS
  ↓
CDN cache MISS
  ↓
App cache MISS (entity_id_mapping)
  ↓
Vitess query (entity ID mapping): 100-200ms
  ↓
Insert new mapping: 50ms
  ↓
App cache populate
  ↓
Vitess query (entity data): 100-200ms
  ↓
RDF Builder (on-demand): 50-100ms
  ↓
Update caches
  ↓
Response time: 300-500ms
```

## Cost Optimization

### Strategy 1: Prefer Cache Over Database

**Rule:** Check all cache layers before querying database

**Cost impact:**
- Valkey: $0.01/10,000 operations (1 cent per 10K ops)
- Vitess: $0.10/10,000 operations (1 cent per 10K ops)
- **10x cheaper** to cache than query database

**Example cost comparison:**
- Database query: 100ms = 1 cent
- Valkey lookup: 1ms = 0.01 cent
- **100x cheaper** to use cache

### Strategy 2: Long TTLs for Immutable Data

**Strategy:**
- S3 snapshots: 1 year (never invalidated)
- entity_id_mapping: 1 hour (never invalidated)
- entity_head: 5 minutes (rarely invalidated)

**Cost impact:**
- Reduces database queries by >90% for hot entities (Q42, Q5, etc.)
- Estimated savings: $500-2000/month at scale

### Strategy 3: CDN Over Direct S3 Access

**Strategy:**
- All public reads go through CDN (CloudFront/Cloudflare)
- CDN caches S3 snapshots for 1 year
- Application only serves cache misses (via S3)

**Cost impact:**
- CDN: $0.085/GB vs S3: $0.09/GB
- Data transfer cost similar, but performance much better
- S3 operations reduced significantly

### Strategy 4: Optimize Cache Memory Usage

**Implementation:**
- Compress cached values (gzip)
- Set appropriate TTL to prevent memory bloat
- Monitor cache size and adjust TTLs

**Example:**
```python
import gzip

def compress_cache_value(value: dict) -> bytes:
    """Compress cache value to reduce memory usage"""
    json_str = json.dumps(value)
    return gzip.compress(json_str.encode('utf-8'))

def decompress_cache_value(compressed: bytes) -> dict:
    """Decompress cache value"""
    return json.loads(gzip.decompress(compressed).decode('utf-8'))
```

## Integration with Existing RDF Builder

### Cache Layer Responsibilities

The **Application Object Cache** is responsible for:
1. **Entity ID lookup** (Q123 → 1424675744195114)
2. **Entity head tracking** (current revision for entity)
3. **Entity metadata** (labels, descriptions for search/browse)
4. **NOT** for storing generated RDF (that's on-demand)

The **RDF Builder** is responsible for:
1. On-demand RDF generation (reading from Vitess using internal_id)
2. No caching of generated RDF (client/browser handles this)
3. Fast response times using cached metadata

### Data Access Pattern

```python
# In API endpoint handler
def get_entity_rdf(external_id: str) -> str:
    """Generate RDF for entity using cached metadata"""
    
    # Step 1: Lookup internal_id from cache
    cache_key = f"entity_id:{external_id}"
    cached = valkey_client.get(cache_key)
    
    if cached:
        # Cache hit - use cached internal_id
        internal_id = json.loads(cached)['internal_id']
    else:
        # Cache miss - query Vitess
        mapping = db.query_one(
            "SELECT internal_id FROM entity_id_mapping WHERE external_id = %s",
            (external_id,)
        )
        if not mapping:
            raise NotFoundError(f"Entity {external_id} not found")
        
        internal_id = mapping['internal_id']
        
        # Populate cache
        cache_value = json.dumps({"internal_id": internal_id})
        valkey_client.setex(cache_key, 3600, cache_value)  # 1 hour TTL
    
    # Step 2: Fetch entity data from Vitess (using internal_id)
    entity_data = db.query_entity_by_internal_id(internal_id)
    
    # Step 3: Generate RDF on-demand
    rdf_builder = EntityConverter(
        property_registry=get_property_registry(),  # From cache
    )
    turtle = rdf_builder.convert_to_string(entity_data)
    
    # Step 4: Add HTTP caching headers
    headers = {
        "ETag": generate_etag(entity_data),
        "Last-Modified": entity_data['modified_at'],
        "Cache-Control": "public, max-age=3600"
    }
    
    return turtle, headers
```

## Cache Warming Strategies

### Initial Warm-up on Deployment

**Purpose:** Pre-populate caches with frequently accessed entities

**Implementation:**
```python
def warm_up_entity_id_cache():
    """Warm up entity_id_mapping cache for top entities"""
    # Query top 10,000 entities by access count (or all if small dataset)
    top_entities = db.query(
        "SELECT external_id, internal_id, entity_type, created_at FROM entity_id_mapping "
        "ORDER BY access_count DESC LIMIT 10000"
    )
    
    # Batch populate cache
    cache.warm_up([e['external_id'] for e in top_entities])
    
    logging.info(f"Warmed up cache for {len(top_entities)} entities")
```

### Periodic Warm-up

**Schedule:** Every 6 hours

**Purpose:** Refresh cache for expired or high-value entities

```bash
# Cron job to warm up cache
0 */6 * * * warm-up-cache.sh
```

## Monitoring

### Key Metrics (from CACHING-STRATEGY.md)

#### Cache Hit Rates

```
entity_id_mapping_cache_hit_rate
  - labels: {cache: valkey}
  - gauge: 0.95-0.99 (target >95%)
  - alert: <90% for >5 minutes

entity_head_cache_hit_rate
  - labels: {cache: valkey}
  - gauge: 0.80-0.90
  - alert: <70% for >5 minutes

client_cache_hit_rate
  - labels: {source: api}
  - gauge: 0.40-0.60
  - alert: <30% for >1 hour

cdn_cache_hit_rate
  - labels: {cdn: cloudfront}
  - gauge: 0.70-0.85
  - alert: <60% for >15 minutes
```

#### Cache Performance

```
cache_lookup_latency_p50
  - labels: {cache: valkey, operation: entity_id_mapping}
  - gauge: <1ms
  - alert: >2ms for >5 minutes

cache_lookup_latency_p99
  - labels: {cache: valkey, operation: entity_id_mapping}
  - gauge: <5ms
  - alert: >10ms for >5 minutes

valkey_memory_usage_bytes
  - gauge: <50GB (for 10M entities, 100 bytes each)
  - alert: >40GB (90% capacity)
  - alert: >45GB (90% capacity)
```

#### Cost Metrics

```
s3_get_operations_total
  - counter: ~1M/week (baseline)
  - alert: >2M/week (cache not effective)

vitess_query_latency_p99
  - gauge: <50ms
  - alert: >100ms (cache not effective)
```

## Implementation Roadmap

### Phase 1: Infrastructure Setup (Week 1-2)
- [ ] Configure Valkey/Memcached cluster
- [ ] Set up S3 bucket with lifecycle policies
- [ ] Configure CDN (CloudFront/Cloudflare)
- [ ] Create Vitess tables (entity_id_mapping, entity_head, entity_revisions)
- [ ] Create entity metadata tables (labels, descriptions)
- [ ] Deploy Application Object Cache
- [ ] Set up monitoring (Prometheus + Grafana)

### Phase 2: Cache Implementation (Week 3-4)
- [ ] Implement entity_id_mapping cache
- [ ] Implement entity_head cache
- [ ] Implement entity_metadata cache
- [ ] Implement cache invalidation logic
- [ ] Add Vitess query caching
- [ ] Implement warm-up scripts
- [ ] Write cache invalidation cron jobs

### Phase 3: RDF Endpoint Integration (Week 5-6)
- [ ] Create API endpoint for entity RDF generation
- [ ] Integrate with Application Object Cache
- [ ] Add HTTP caching headers
- [ ] Implement compression (gzip, Brotli)
- [ ] Add Prometheus metrics
- [ ] Load testing and optimization

### Phase 4: S3 Integration (Week 7-8)
- [ ] Implement S3 snapshot writer
- [ ] Configure CDN distribution
- [ ] Set up lifecycle policies
- [ ] Create revision storage pattern
- [ ] Test CDN caching behavior

### Phase 5: Optimization (Week 9-10)
- [ ] Analyze cache hit rates and optimize TTLs
- [ ] Implement cache warm-up scheduling
- [ ] Optimize database queries (add indexes)
- [ ] Implement CDN bypass for cache misses
- [ ] Performance testing at scale

## Trade-offs and Considerations

### On-Demand vs Pre-Generated RDF

**On-Demand (our approach):**
- ✅ Always fresh data
- ✅ No storage costs for pre-generated dumps
- ✅ Can handle very large entities efficiently
- ✅ Matches MediaWiki's approach
- ❌ Higher per-request latency (50-200ms)
- ❌ Higher database load

**Pre-Generated (Wikidata's approach):**
- ✅ Very fast (serve static file)
- ✅ No database load for reads
- ✅ Minimal application CPU
- ❌ Data can be up to 1 week stale
- ❌ High storage costs (petabytes of RDF)
- ❌ Complex change propagation (must regenerate all dependent dumps)

**Our Hybrid Strategy:**
- Use caching for fast lookups (metadata, labels)
- Generate RDF on-demand (ensures freshness)
- Cache only what's cheap (metadata, not expensive full RDF)
- Balance between freshness and cost

### Cache Layer Selection

When to use which cache layer:

| Data Type | Best Cache Layer | Rationale |
|------------|------------------|-----------|
| External ID → Internal ID | entity_id_mapping | Never changes, cache indefinitely |
| Entity head | entity_head cache | Changes frequently, need short TTL (5 min) |
| Entity labels/descriptions | entity_metadata cache | Change occasionally, medium TTL (30 min) |
| Entity data | S3 (immutable) | Generate on-demand, cache only via CDN |

### Change Detection and Propagation

**Challenge:** How do we know when to invalidate caches?

**Solution:**
1. **Entity metadata tables in Vitess:** Track entity `modified_at` timestamp
2. **Revision tracking:** New revision ID on each update
3. **Cache invalidation:** Invalidate all related caches on entity update
4. **Event streaming:** Subscribe to Vitess change events for real-time updates

**Simple approach (MVP):**
- Use `modified_at` timestamp from entity table
- Invalidate entity_head and entity_metadata caches on every update
- Let entity_id_mapping cache expire naturally (1 hour)

## MVP Implementation Plan

### Week 1: Core Caching (Minimal Viable Product)

**Goal:** 70-80% cache hit rate for hot entities, <200ms response time

**Scope:**
1. Deploy single Valkey instance (or Memcached cluster)
2. Create entity_id_mapping cache layer
3. Implement simple cache invalidation (1-hour TTL)
4. Add HTTP caching headers to API responses
5. Basic monitoring (cache hit rates, response times)

**What's NOT in scope:**
- Entity head cache
- Entity metadata cache
- S3 snapshots
- CDN distribution
- Warm-up scripts

**Week 2:** Extended Caching

**Scope:**
1. Add entity_head cache
2. Add entity_metadata cache
3. Implement proper cache invalidation logic
4. Add warm-up scripts
5. Advanced monitoring (Grafana dashboards)

**Week 3-4:** Performance Optimization

**Scope:**
1. Database query optimization (add indexes)
2. Vitess query caching
3. API response compression
4. Load testing and optimization
5. CDN integration (optional)

**Week 5+:** S3 Integration (Optional)

**Scope:**
1. S3 snapshot writer
2. CDN configuration
3. Lifecycle policies
4. Global replication

## Success Criteria

### Performance Targets

- [ ] P50 latency < 120ms for hot entities (cached)
- [ ] P99 latency < 200ms for hot entities (cached)
- [ ] P50 latency < 400ms for cold entities (not cached)
- [ ] entity_id_mapping cache hit rate > 95%
- [ ] entity_head cache hit rate > 80%
- [ ] entity_metadata cache hit rate > 70%

### Cost Targets

- [ ] < 100ms Vitess query latency (cache hit)
- [ ] Valkey cost < $200/month at target scale
- [ ] S3 cost < $100/month at target scale
- [ ] CDN cost < $50/month (if used)

### Reliability

- [ ] 99.9% uptime
- [ ] Graceful degradation (serve from cache if database unavailable)
- < 1 minute MTTR (Mean Time To Recover)

## Next Steps

1. **Review this document** with team to validate architecture
2. **Estimate infrastructure requirements** (Valkey size, S3 storage, bandwidth)
3. **Create detailed implementation plan** for MVP (Week 1)
4. **Set up monitoring strategy** (Prometheus, Grafana, alerting)
5. **Prioritize features** based on business value (latency vs. cost)

## References

- **[CACHING-STRATEGY.md](./CACHING-STRATEGY.md)** - Detailed caching strategy
- **[IDENTIFIER-STRATEGY.md](./IDENTIFIER-STRATEGY.md)** - Entity ID strategy (hybrid internal/external)
- **[STORAGE-ARCHITECTURE.md](../STORAGE-ARCHITECTURE.md)** - Vitess database design
- **[ENTITY-MODEL.md](../ENTITY-MODEL.md)** - Entity data model
- **[STORAGE-ARCHITECTURE.md](./STORAGE-ARCHITECTURE.md)** - S3 storage design
- **[SCALING-PROPERTIES.md](../SCALING-PROPERTIES.md)** - System scaling characteristics
