# Caching Strategy and Cost Control

## Overview

Wikibase backend uses multiple cache layers to achieve sub-second response times while controlling infrastructure costs. This strategy is designed for 1M+ entities/week scale with efficient hit rates and appropriate TTL policies.

## Cache Architecture

```
Client Request
    ↓
┌───────────────────────────────────────┐
│ 1. Browser/Client Cache           │
│    - HTTP caching headers            │
│    - ETag / Last-Modified        │
│    - Max-age directives           │
└───────────────────────────────────────┘
    ↓ (cache miss)
┌───────────────────────────────────────┐
│ 2. CDN Cache                     │
│    - CloudFront / Cloudflare      │
│    - Edge location caching         │
│    - S3 snapshots (immutable)     │
│    - Cache-Control: public, max-age=31536000 (1 year) │
└───────────────────────────────────────┘
    ↓ (CDN miss)
┌───────────────────────────────────────┐
│ 3. Application Object Cache          │
│    - Valkey / Memcached           │
│    - entity_id_mapping lookups     │ ← NEW: Hybrid ID translation
│    - entity_head lookups         │
│    - entity metadata              │
└───────────────────────────────────────┘
    ↓ (object cache miss)
┌───────────────────────────────────────┐
│ 4. Vitess Database                │
│    - entity_id_mapping table      │
│    - entity_head table            │
│    - entity_revisions table        │
└───────────────────────────────────────┘
    ↓ (database miss)
┌───────────────────────────────────────┐
│ 5. S3 Object Store               │
│    - Immutable snapshots           │
│    - S3 GET operations           │
└───────────────────────────────────────┘
```

## Cache Layers

### Layer 1: Client Cache

**Purpose:** Eliminate redundant requests from clients

**Mechanism:**
- HTTP caching headers (ETag, Last-Modified)
- Cache-Control directives
- Conditional requests (If-None-Match, If-Modified-Since)

**Configuration:**
```http
Cache-Control: public, max-age=3600, s-maxage=86400
ETag: "revision_id:content_hash"
Last-Modified: revision.created_at
```

**Expected hit rate:** 40-60% (depending on client usage patterns)

---

### Layer 2: CDN Cache (Optional)

**Purpose:** Serve immutable snapshots from edge locations worldwide

**Key characteristics:**
- **Immutable snapshots**: S3 objects never change after write
- **Infinite cacheability**: No invalidation needed
- **Edge delivery**: Sub-50ms latency globally

**S3 Cache Configuration:**
```yaml
S3 Object Metadata:
  Cache-Control: "public, max-age=31536000, immutable"  # 1 year
  Expires: 1 year from now
  x-amz-meta-revision-id: "42"
  x-amz-meta-content-hash: "sha256:..."
```

**CDN Configuration (CloudFront/Cloudflare):**
- Cache S3 GET responses for 1 year
- Enable Gzip/Brotli compression
- Enable HTTP/2 and HTTP/3

**Expected hit rate:** 70-85% for hot entities (Q42, Q5, etc.)

---

### Layer 3: Application Object Cache

**Purpose:** Cache database queries and identifier mappings

**Technologies:** Valkey (recommended) or Memcached

#### 3.1 Entity ID Mapping Cache (NEW for Hybrid ID Strategy)

**Purpose:** Cache `entity_id_mapping` lookups for fast external → internal ID translation

**Cache key format:**
```
entity_id:{external_id}
Examples:
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
- Mappings rarely change after creation
- Long enough to handle load spikes
- Short enough to pick up changes if needed

**Implementation:**

```python
from redis import redis
import json

class EntityIdCache:
    def __init__(self, valkey_client: redis.Redis):
        self.valkey = valkey_client  # Valkey uses redis-py client (Redis-compatible)
        self.ttl = 3600  # 1 hour
        self.key_prefix = "entity_id:"
    
    def get_internal_id(self, external_id: str) -> int:
        """Lookup internal_id by external_id (Q123, P42, L999)"""
        cache_key = f"{self.key_prefix}{external_id}"
        cached = self.valkey.get(cache_key)
        
        if cached:
            # Cache hit
            cache_data = json.loads(cached)
            return cache_data['internal_id']
        
        # Cache miss: query database
        result = db.query(
            "SELECT internal_id, entity_type, created_at FROM entity_id_mapping WHERE external_id = %s",
            (external_id,)
        )
        if not result:
            raise NotFoundError(f"Entity {external_id} not found")
        
        # Populate cache
        cache_value = json.dumps({
            "internal_id": result['internal_id'],
            "entity_type": result['entity_type'],
            "created_at": str(result['created_at'])
        })
        self.valkey.setex(cache_key, self.ttl, cache_value)
        
        return result['internal_id']
    
    def invalidate(self, external_id: str):
        """Invalidate cache entry on entity update/delete"""
        cache_key = f"{self.key_prefix}{external_id}"
        self.valkey.delete(cache_key)
    
    def warm_up(self, external_ids: list[str]):
        """Warm up cache for frequently accessed entities"""
        with self.valkey.pipeline() as pipe:
            for external_id in external_ids:
                cache_key = f"{self.key_prefix}{external_id}"
                # Query database (batch)
                results = db.query_batch(
                    "SELECT internal_id, entity_type, created_at FROM entity_id_mapping WHERE external_id IN (%s)" % 
                    ','.join(['%s'] * len(external_ids)),
                    external_ids
                )
                for result in results:
                    cache_value = json.dumps({
                        "internal_id": result['internal_id'],
                        "entity_type": result['entity_type'],
                        "created_at": str(result['created_at'])
                    })
                    pipe.setex(cache_key, self.ttl, cache_value)
            pipe.execute()
```

#### 3.2 Entity Head Cache

**Purpose:** Cache current head revision pointer to avoid frequent `entity_head` table queries

**Cache key format:**
```
entity_head:{internal_id}
Example:
  entity_head:1424675744195114
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
- Head revisions update frequently on active entities
- Short TTL to stay current

#### 3.3 Entity Metadata Cache

**Purpose:** Cache entity metadata (labels, descriptions, types) for search and browse endpoints

**Cache key format:**
```
entity_meta:{internal_id}
Example:
  entity_meta:1424675744195114
```

**Cache value:**
```json
{
  "internal_id": 1424675744195114,
  "external_id": "Q123",
  "entity_type": "item",
  "labels": {"en": "Douglas Adams", "de": "Douglas Adams"},
  "descriptions": {"en": "British author"}
}
```

**TTL:** 1800 seconds (30 minutes)

---

### Layer 4: Vitess Database Query Cache

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

---

### Layer 5: S3 Object Store

**Purpose:** System of record for all entity snapshots

**Characteristics:**
- **Immutable**: Never modified after write
- **Cache-friendly**: CDN caches for 1 year
- **Global replication**: Multi-region S3 for low latency

**No caching strategy needed** at S3 layer due to immutability.

---

## Cache Invalidation Strategy

### Immutable Data (No Invalidation)

**S3 Snapshots:**
- **Never invalidated** - immutable by design
- If content is wrong, create new revision

**entity_id_mapping (after creation):**
- **Rarely changes** - mapping is immutable
- Only invalidated if entity is deleted and recreated (very rare)

### Mutable Data (Active Invalidation)

**entity_head (head revision pointer):**
- **Invalidated on successful write**
- **TTL fallback**: 5 minutes ensures eventual correctness

**Entity metadata (labels, descriptions):**
- **Invalidated on entity update**
- **TTL fallback**: 30 minutes

### Invalidation Implementation

```python
class CacheInvalidator:
    def invalidate_entity(self, external_id: str, internal_id: int):
        """Invalidate all cache entries for entity"""
        # 1. Invalidate entity_id_mapping cache
        entity_id_cache.invalidate(external_id)
        
        # 2. Invalidate entity_head cache
        entity_head_cache_key = f"entity_head:{internal_id}"
        valkey_client.delete(entity_head_cache_key)
        
        # 3. Invalidate entity metadata cache
        entity_meta_cache_key = f"entity_meta:{internal_id}"
        valkey_client.delete(entity_meta_cache_key)
        
        # 4. Clear CDN cache (if needed)
        # Note: S3 snapshots are immutable, no CDN invalidation needed

# Example: Invalidate after entity update
def update_entity(entity_data: dict):
    external_id = entity_data['external_id']
    internal_id = entity_data['internal_id']
    
    # Write new S3 snapshot
    s3.put(f"revisions/{external_id}/r{entity_data['revision_id']}.json", entity_data)
    
    # Update Vitess (CAS update entity_head)
    db.update_entity_head(internal_id, entity_data['revision_id'])
    
    # Invalidate caches
    cache_invalidator.invalidate_entity(external_id, internal_id)
    
    return {"status": "success"}
```

---

## Performance Targets

### Expected Hit Rates

| Cache Layer | Expected Hit Rate | Target P50 Latency | Target P99 Latency |
|-------------|------------------|---------------------|---------------------|
| **Client cache** | 40-60% | 0ms (local) | 0ms (local) |
| **CDN cache** | 70-85% | 50ms | 200ms |
| **entity_id_mapping cache** | >95% | <1ms | <5ms |
| **entity_head cache** | 80-90% | <2ms | <10ms |
| **Entity metadata cache** | 70-80% | <5ms | <20ms |
| **Vitess query cache** | 30-40% | <10ms | <50ms |

### Latency Targets

```
GET /entity/Q123 (hot entity, cached)
    ↓ Client cache HIT:      <1ms (local)
GET /entity/Q123 (hot entity, not in client cache)
    ↓ CDN HIT:              50ms (edge)
GET /entity/Q123 (cold entity)
    ↓ CDN MISS → object cache HIT:  60ms
    ↓ Object cache MISS → Vitess:     100ms
    ↓ Vitess → S3:                        200ms (total P99)
```

---

## Cost Control

### Cost Optimization Strategies

#### 1. Prefer Cache Over Database

**Rule:** Check all cache layers before querying database

**Cost impact:**
- Valkey: $0.01/10,000 operations
- Vitess: $0.10/10,000 operations
- **10x cheaper** to cache

#### 2. Long TTLs for Immutable Data

**Strategy:**
- S3 snapshots: 1 year (never invalidated)
- entity_id_mapping: 1 hour (rarely changes)

**Cost impact:**
- Reduces database queries by >90% for hot entities
- Estimated savings: $500-2000/month at scale

#### 3. CDN Over Direct S3 Access

**Strategy:**
- All public reads go through CDN (CloudFront/Cloudflare)
- CDN caching reduces S3 GET operations by 80%

**Cost impact:**
- CDN: $0.085/GB (vs S3: $0.09/GB)
- Data transfer cost similar, but performance much better
- S3 operations reduced significantly

#### 4. Optimize Cache Memory Usage

**Strategy:**
- Compress cached values (gzip)
- Use efficient data structures
- Set appropriate TTL to prevent memory bloat

**Implementation:**

```python
import gzip

def compress_cache_value(value: dict) -> bytes:
    """Compress cache value to reduce memory usage"""
    json_str = json.dumps(value)
    return gzip.compress(json_str.encode('utf-8'))

def decompress_cache_value(compressed: bytes) -> dict:
    """Decompress cache value"""
    return json.loads(gzip.decompress(compressed).decode('utf-8'))

# Usage in cache
cache_value = {"internal_id": 1424675744195114, ...}
compressed = compress_cache_value(cache_value)
valkey_client.set("entity_id:Q123", compressed)

# Decompress on read
compressed = valkey_client.get("entity_id:Q123")
cache_value = decompress_cache_value(compressed)
```

---

## Monitoring

### Key Metrics

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

cdn_cache_hit_rate
  - labels: {cdn: cloudfront}
  - gauge: 0.70-0.85
  - alert: <60% for >15 minutes

client_cache_hit_rate
  - labels: {source: api}
  - gauge: 0.40-0.60
  - alert: <30% for >1 hour
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

cdn_bytes_served_total
  - counter: ~10TB/week
  - target: >80% of traffic
```

---

## Warm-up Strategies

### Initial Warm-up on Deployment

**Purpose:** Pre-populate caches with frequently accessed entities

**Strategy:**

```python
def warm_up_entity_id_cache():
    """Warm up entity_id_mapping cache for top entities"""
    # Query top 10,000 entities by access count (or all if small dataset)
    top_entities = db.query(
        "SELECT external_id, internal_id, entity_type FROM entity_id_mapping "
        "ORDER BY access_count DESC LIMIT 10000"
    )
    
    # Batch populate cache
    cache.warm_up([e['external_id'] for e in top_entities])
    
    logging.info(f"Warmed up cache for {len(top_entities)} entities")

# Run on deployment
warm_up_entity_id_cache()
```

### Periodic Warm-up

**Schedule:** Every 6 hours

**Purpose:** Refresh cache for entities that expired

**Implementation:**
```cron
# Cron job to warm up cache
0 */6 * * * * warm-up-cache.sh
```

---

## Configuration

### Valkey Configuration

```yaml
# valkey.conf
maxmemory 64gb
maxmemory-policy allkeys-lru  # Evict least recently used keys
save 900 1                 # Save to disk every 15 minutes if 1+ changes
save 300 10                # Save every 5 minutes if 10+ changes
save 60 10000              # Save every minute if 10000+ changes
appendonly yes               # AOF persistence for durability
tcp-keepalive 300           # Keep connections alive
timeout 300                 # Close idle connections after 5 minutes
```

### Cache Client Configuration

```python
# Python redis-py client (Valkey-compatible)
from redis import redis

valkey_client = redis.Redis(
    host='valkey.internal',
    port=6379,
    db=0,
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30,
    max_connections=50
)
```

---

## Operational Procedures

### Cache Clearing

**Full cache clear (emergency):**

```bash
# Flush all Valkey keys (use with caution)
valkey-cli FLUSHDB

# Verify cache is empty
valkey-cli DBSIZE
```

**Selective cache clear:**

```bash
# Clear only entity_id_mapping cache
valkey-cli --scan --pattern 'entity_id:*' | xargs valkey-cli DEL

# Clear only entity_head cache
valkey-cli --scan --pattern 'entity_head:*' | xargs valkey-cli DEL
```

### Cache Backfill

**Scenario:** Cache cleared or Valkey replaced

**Procedure:**

```python
def backfill_entity_id_cache():
    """Backfill entity_id_mapping cache from database"""
    # Query all entity_id_mapping records
    all_mappings = db.query(
        "SELECT external_id, internal_id, entity_type, created_at "
        "FROM entity_id_mapping ORDER BY created_at"
    )
    
    # Batch populate cache
    batch_size = 1000
    for i in range(0, len(all_mappings), batch_size):
        batch = all_mappings[i:i+batch_size]
        cache.warm_up([m['external_id'] for m in batch])
        logging.info(f"Backfilled {i+batch_size}/{len(all_mappings)} mappings")
        time.sleep(0.1)  # Prevent overwhelming Valkey
```

---

## References

- [IDENTIFIER-STRATEGY.md](./IDENTIFIER-STRATEGY.md) - Hybrid ID strategy (internal ulid-flake + external Q123)
- [STORAGE-ARCHITECTURE.md](STORAGE-ARCHITECTURE.md) - S3 + Vitess storage design
- [ENTITY-MODEL.md](ENTITY-MODEL.md) - Entity identifiers and usage patterns
- [SCALING-PROPERTIES.md](SCALING-PROPERTIES.md) - System scaling characteristics
