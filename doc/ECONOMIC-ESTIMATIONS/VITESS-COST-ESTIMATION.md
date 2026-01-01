# Vitess Database Cost Estimation

## Overview

This document estimates Vitess database and Kubernetes cluster costs for storing metadata and indexing for 1 billion Wikibase entities at scale.

**Important Note:** All calculations use AWS GKE pricing for estimates. Expect at least 10% overhead when running on Wikimedia Foundation (WMF) infrastructure due to additional operational costs, internal services, and compliance requirements.

## Executive Summary

**Vitess strategy:** Store pointers and metadata only (entity content in S3)

**Key findings:**
- Total data: 5.05 TB (Year 1) → 12.6 TB (Year 10)
- Cluster: 16 nodes, 44 cores, 112 GB RAM
- Sharding: Start with 24 shards, scale to 64 by Year 10
- Query load: 50 QPS peak (Wikidata's 10 edits/sec rate)
- Annual cost: ~$22,496 (plus 10% WMF overhead = ~$24,746)
- 10-year cost: ~$224,960 (plus 10% WMF overhead = ~$247,456)

**Comparison to S3 storage costs:**
- Vitess: ~2% of S3 storage costs at Year 10 scale
- Highly cost-effective as metadata/indexing layer

## Data Model Analysis

### Vitess Tables (from STORAGE-ARCHITECTURE.md)

Vitess stores **pointers and metadata**, never entity content (stored in S3).

| Table | Purpose | Rows | Row Size | Total Size |
|-------|---------|-------|-----------|----------|
| entity_head | Current revision pointer | 1B | 50 bytes | 50 GB |
| entity_revisions | Revision history | 20B (avg 20/entity) | 100 bytes | 2.0 TB |
| entity_revision_meta | Validation metadata | 20B | 150 bytes | 3.0 TB |
| entity_delete_audit | Deletion tracking | 1M (0.1% deletion rate) | 200 bytes | 0.2 GB |
| **Total** | - | - | **~5.05 TB** |

### Growth Model

**Growth based on entity count:**

| Year | Entities | Revisions | Total Data | Per Shard (24 shards) |
|------|-----------|------------|-------------|----------------------|
| Year 1 | 1B | 20B | 5.05 TB | ~210 GB |
| Year 2 | 1.1B | 22B | 5.56 TB | ~232 GB |
| Year 3 | 1.21B | 24.2B | 6.11 TB | ~255 GB |
| Year 5 | 1.5B | 30B | 7.58 TB | ~316 GB |
| Year 10 | 2.5B | 50B | 12.6 TB | ~525 GB |

**Vitess recommendation:** 250GB per MySQL server (shard) for 15-minute recovery time from backup.

## Sharding Strategy

### Vitess Sharding Recommendations

From Vitess official documentation:
- **Recommended shard size:** 250GB per MySQL server
- **Reasoning:** Fast recovery times (15 minutes), manageable backup/restore operations
- **Hard limit:** 64TB per InnoDB tablespace (not practical limit)

### Initial Sharding (Year 1)

**Starting configuration:**
- Total data: 5.05 TB
- Shard size target: 250GB
- Shards needed: 5.05 TB ÷ 250 GB = 20.2
- **Deployment: 24 shards** (for headroom and balanced distribution)

**Per-shard capacity:**
- Data per shard: 5.05 TB ÷ 24 = ~210 GB
- Headroom: 40 GB (16%)
- **Status:** Comfortable for 1-2 years without resharding

### Future Sharding (Year 10)

**Growth to 2.5B entities:**
- Total data: 12.6 TB
- Shards needed: 12.6 TB ÷ 250 GB = 50.4
- **Deployment: 64 shards** (power-of-two scaling)

**Resharding strategy:**
- Incremental: 24 → 32 → 48 → 64 shards
- Timeline: Reshard every 2-3 years as data grows
- Method: Vitess built-in resharding tools

## Query/Write Load Estimation

### Wikidata Edit Rate

**Actual Wikidata measurements:**
- Edits/sec: ~10 (measured)
- Edits/day: ~864,000
- Edits/year: ~315 million

### Write Operations

**Per edit:**
1. Validate entity JSON
2. Assign next revision_id
3. Write snapshot to S3
4. Insert revision metadata into Vitess (1 row)
5. Update entity_head (1 row, CAS operation)
6. Emit change event

**Write QPS:**
- Entity revision inserts: 10 QPS
- Entity head updates: 10 QPS
- Validation metadata: 10 QPS
- **Total writes: 30 QPS**
- Peak with 2x headroom: 60 QPS

### Read Operations

**API request patterns (from CACHING-STRATEGY.md):**
- 80% cache hit rate (conservative)
- 20% queries reach Vitess
- CDN cache reduces S3 GET operations by 80%

**Read QPS:**
- Total API requests: 50 QPS
- Cache hits (Valkey + application cache): 40 QPS (80%)
- **Vitess queries: 10 QPS** (20% cache miss)
- Worst case (no cache): 50 QPS to Vitess

### Total Vitess QPS

| Scenario | Reads | Writes | Total |
|----------|--------|--------|--------|
| Normal (80% cache hit) | 10 | 30 | 40 |
| Peak (50% cache hit) | 25 | 60 | 85 |
| Worst case (0% cache hit) | 50 | 60 | 110 |

## Kubernetes Cluster Requirements

### Vitess Component Sizing

**From Vitess FAQ and best practices:**

| Component | Purpose | Cores per Unit | Units | Total Cores |
|-----------|---------|----------------|-------|------------|
| VTGate | Query routing | 2-4 | 2 | 4 |
| VTTablet + MySQL | Shard storage | 1-2 | 24 | 36 |
| vtctld | Schema management | 1 | 1 | 1 |
| vtorc | Tablet orchestration | 0.5 | 1 | 0.5 |
| **Total** | - | - | **41.5** |

**Memory sizing (Vitess recommendation: 4 GB per 250GB shard):**

| Component | RAM per Unit | Units | Total RAM |
|-----------|--------------|-------|-----------|
| VTGate | 4 GB | 2 | 8 GB |
| VTTablet + MySQL | 4 GB | 24 | 96 GB |
| vtctld | 2 GB | 1 | 2 GB |
| vtorc | 2 GB | 1 | 2 GB |
| **Total** | - | - | **108 GB** |

### Pod Configuration

**Pod requirements:**

| Component | Replicas | CPU | Memory | Storage per Pod |
|-----------|-----------|------|---------|----------------|
| VTGate | 2 | 2 cores | 4 GB | - |
| VTTablet Primary | 12 | 1.5 cores | 4 GB | 600 GB |
| VTTablet Replica | 12 | 1.5 cores | 4 GB | 600 GB |
| vtctld | 1 | 1 core | 2 GB | - |
| vtorc | 1 | 0.5 cores | 2 GB | - |
| **Total** | **28** | **41.5 cores** | **108 GB** | - |

### Node Requirements

**Node sizing (conservative):**

| Node Type | Count | CPU | Memory | Storage | Purpose |
|-----------|--------|------|---------|---------|
| Database nodes | 12 | 4 cores × 12 = 48 cores | 8 GB × 12 = 96 GB | 1 primary + 1 replica per shard |
| Application nodes | 2 | 8 cores × 2 = 16 cores | 16 GB × 2 = 32 GB | VTGate, vtctld, vtorc |
| **Total** | **14 nodes** | **64 cores** | **128 GB** | - |

**Recommendation:** Use 16 nodes (2 additional for maintenance/HA)

### Storage per Node

**Database node storage:**
- Shard size: 250 GB (recommended maximum)
- MySQL data directory: 250 GB
- Binlog/WAL: 50 GB
- Temporary space: 50 GB
- **Total per node: ~600 GB**

**Total cluster storage:**
- 12 nodes × 600 GB = 7.2 TB

**Note:** Backups stored separately (not included in node sizing)

## Cost Estimation

### Compute Costs (GKE, us-central1)

**Pricing:** n1-standard-4 (4 vCPU, 16 GB RAM) at $0.10/hour

| Node Type | Count | Hourly Cost | Monthly Cost |
|-----------|--------|-------------|--------------|
| Database nodes | 12 | 12 × $0.10 = $1.20 | $876 |
| Application nodes | 2 | 2 × $0.10 = $0.20 | $146 |
| **Total** | **14** | **$1.40/hour** | **$1,022/month** |

**With 16 nodes (including 2 extra):**
- Hourly: 16 × $0.10 = $1.60
- Monthly: $1.60 × 730 = $1,168/month

### Storage Costs (GKE)

**Pricing:** pd-ssd at $0.10/GB/month

| Storage Type | Size | Monthly Cost |
|-------------|-------|-------------|
| Database node storage | 12 nodes × 600 GB = 7.2 TB | $720 |
| **Total** | **7.2 TB** | **$720/month** |

### Network Costs

**Estimated traffic:**
- Internal cluster communication: ~10 GB/day
- External API traffic: ~5 GB/day
- S3 fetch traffic: ~20 GB/day
- **Total: ~35 GB/day = ~1 TB/month**

**Network cost:**
- Egress: $0.12/GB × 1,000 GB = $120/month

### Total Monthly Cost

| Component | Monthly Cost | Annual Cost |
|-----------|--------------|-------------|
| Compute (16 nodes) | $1,168 | $14,016 |
| Storage (7.2 TB) | $720 | $8,640 |
| Network | $120 | $1,440 |
| **Total** | **$2,008** | **$24,096** |

### WMF Infrastructure Overhead

**Required overhead:** Minimum 10%

**Reasons for overhead:**
- Internal network infrastructure
- Operational support and monitoring
- Compliance and security requirements
- Redundancy and backup systems
- Shared infrastructure costs

**Total annual cost with 10% overhead:**
```
$24,096 × 1.10 = $26,506/year
```

### 10-Year Cost Projection

**Vitess costs (constant each year):**
- Annual cost: $24,096
- 10-year cost: $240,960

**With 10% WMF overhead:**
- Annual: $26,506
- 10-year: $265,060

## Cost Comparison

### Vitess vs. S3 Storage

From STORAGE-COST-ESTIMATIONS.md:

| Cost Component | Annual Cost | 10-Year Cost |
|---------------|-------------|--------------|
| S3 storage (Year 10 scale) | $227,832 | $2.28M |
| Vitess (AWS) | $24,096 | $240,960 |
| Vitess (WMF +10%) | $26,506 | $265,060 |
| **Vitess % of S3** | **11.6%** | **11.6%** |

**Conclusion:** Vitess represents ~12% of S3 storage costs, highly efficient as metadata/indexing layer.

### Baseline: Single-Node Database

**Comparison to non-sharded approach:**

| Approach | Nodes | CPU | RAM | Annual Cost | 10-Year Cost |
|----------|--------|------|-------------|--------------|
| Single MySQL (no sharding) | 1 | 16 cores | $1,920 | $19,200 |
| Vitess (24 shards) | 16 | 64 cores | $26,506 | $265,060 |

**Analysis:**
- Vitess costs 13.8x more than single node
- But provides: Horizontal scalability, fault isolation, resharding capability, built-in replication
- Single node cannot scale to 1B entities (physical limits)
- **Conclusion:** Vitess cost premium is justified by scalability benefits

## Scaling Strategy

### Phase 1: Start (Weeks 1-4)

**Initial deployment:**
- 12 shards
- 12 database nodes (6 primary + 6 replica)
- 2 application nodes
- Handle up to 30 QPS
- Support 500M entities

### Phase 2: Scale (Months 2-6)

**Expand to 24 shards:**
- 24 database nodes (12 primary + 12 replica)
- 4 application nodes
- Handle up to 85 QPS (peak)
- Support 1B entities

### Phase 3: Future (Years 2-10)

**Incremental resharding:**
- 24 → 32 shards (Year 2-3)
- 32 → 48 shards (Year 4-6)
- 48 → 64 shards (Year 7-10)
- Support 2.5B entities by Year 10

### Resharding Costs

**Per resharding operation:**
- Temporary nodes for migration: 4 nodes × 1 week = $384
- Downtime: Near-zero (Vitess live resharding)
- **Annual resharding cost: ~$384 (every 2-3 years)

## Performance Characteristics

### Query Latency

**From CACHING-STRATEGY.md:**

| Layer | Latency | Hit Rate |
|-------|---------|----------|
| Valkey (cache) | <1ms | 80% |
| Vitess (cache miss) | 100-200ms | 20% |
| S3 (entity fetch) | 200-500ms | 16% (after Vitess miss) |

### Bottleneck Analysis

**Capacity:**
- VTGate: 4 cores = ~8,000 QPS capacity
- VTTablet: 36 cores = ~54,000 QPS capacity
- **Required: 40-110 QPS**
- **Headroom:** 73x (VTGate), 491x (VTTablet)

**Conclusion:** Significant headroom with 24 shards and 80% cache hit rate.

## Monitoring Requirements

### Key Metrics

**Vitess-specific metrics:**
- Shard health and replication lag (<5 seconds target)
- Query latency (p50 <100ms, p95 <200ms, p99 <500ms)
- Cache hit rates (>80% target)
- CPU/memory utilization per pod (<70% target)
- Disk I/O per shard
- Network throughput between pods

**Kubernetes metrics:**
- Pod restart rates
- Node resource utilization
- Pod pending/unschedulable count
- Network latency between nodes

### Alerting Thresholds

**Vitess alerts:**
- Replication lag >10 seconds
- Query latency p99 >500ms for 5+ minutes
- CPU >70% for 10+ minutes
- Disk usage >80%

**Kubernetes alerts:**
- Pod crash loop >3 restarts
- Node not ready >5 minutes
- Resource quota exceeded

## Risk Assessment

### High-Risk Items

**1. Resharding complexity**
- **Risk:** Large-scale resharding operations can fail or cause issues
- **Probability:** Low (Vitess mature tooling)
- **Impact:** Medium (downtime, data inconsistency)
- **Mitigation:** Test thoroughly, gradual resharding, maintain backups

### Medium-Risk Items

**1. Cache hit rate lower than expected**
- **Risk:** Actual cache hit rate <80%, increasing Vitess load
- **Probability:** Medium (conservative estimate)
- **Impact:** Medium (higher Vitess QPS, need more resources)
- **Mitigation:** Monitor closely, scale VTTablets if needed

**2. Replication lag**
- **Risk:** Replicas fall behind primary, stale reads
- **Probability:** Low (Vitess built-in replication)
- **Impact:** Medium (stale data, consistency issues)
- **Mitigation:** Monitor lag, use primary for critical reads, scale replicas

### Low-Risk Items

**1. Cost overruns**
- **Risk:** Actual costs higher than estimates
- **Probability:** Low (conservative sizing)
- **Impact:** Low (manageable cost scale)
- **Mitigation:** Monitor monthly spend, right-size resources

**2. Resource exhaustion**
- **Risk:** Insufficient CPU/RAM for workload
- **Probability:** Low (73x headroom calculated)
- **Impact:** Low (scale horizontally, add shards)
- **Mitigation:** Autoscale policies, capacity planning

## Recommendations

### Primary Recommendation

**Deploy Vitess with 24 shards starting from day 1**

**Key benefits:**
- Immediate support for 1B entities
- 16% headroom per shard (210 GB vs. 250 GB target)
- No immediate resharding required
- Manageable annual cost: ~$26,506
- 12% of S3 storage costs (highly efficient)

### Secondary Recommendations

1. **Start with conservative cache hit rate (80%)** - Plan for higher Vitess load initially
2. **Monitor actual cache hit rates** - Adjust resource allocation based on real data
3. **Plan for resharding by Year 2-3** - Don't wait until shards hit limits
4. **Single-region deployment initially** - Add multi-region only if disaster recovery needs require it
5. **Use GKE autoscaling** - Enable HPA for VTGate based on QPS

### Implementation Priority

**Phase 1 (Immediate):**
- Deploy 12-shard Vitess cluster
- Configure replication (1 primary + 1 replica)
- Set up monitoring and alerting
- Configure query caching

**Phase 2 (Months 1-3):**
- Expand to 24 shards
- Monitor performance at scale
- Tune cache parameters
- Optimize query plans

**Phase 3 (Months 3-12):**
- Prepare resharding plan for Year 2-3
- Establish backup strategy
- Document operational procedures
- Train team on Vitess operations

## Summary

**Total annual cost:** ~$26,506 (GKE pricing + 10% WMF overhead)
**10-year cost:** ~$265,060
**Cost relative to S3:** ~12% of S3 storage costs at Year 10 scale
**Cluster size:** 16 nodes, 64 cores, 128 GB RAM, 24 shards
**Capacity:** 40-110 QPS (73-491x headroom)
**Scalability:** Horizontal scaling to 64 shards by Year 10

**Conclusion:** Vitess is highly cost-effective as the metadata/indexing layer, providing horizontal scalability and fault tolerance at a fraction of S3 storage costs. The 24-shard starting configuration provides immediate support for 1B entities with headroom for growth.

---

**Document version:** 1.0
**Last updated:** January 1, 2026
**Author:** Backend team
**Status:** Draft for review

**Related documents:**
- STORAGE-COST-ESTIMATIONS.md - S3 storage cost analysis
- STORAGE-ARCHITECTURE.md - Vitess database design
- CACHING-STRATEGY.md - Cache layer architecture
- SCALING-PROPERTIES.md - Scaling characteristics
