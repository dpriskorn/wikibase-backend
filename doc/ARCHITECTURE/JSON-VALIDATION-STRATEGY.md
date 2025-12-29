# JSON Validation Strategy

## Overview

This document evaluates two architectural approaches for handling JSON validation in the Wikibase backend API, focusing on the trade-offs between performance and data integrity.

## Options Comparison

### Option A: Accept Any Valid JSON (Recommended)

Accept syntactically valid JSON at the API layer without schema validation before persistence.

### Option B: Validate Against Schema Before Acceptance

Validate JSON against a defined schema before accepting and persisting the entity.

---

## Option A: Accept Any Valid JSON

### Pros

#### Performance
- **No validation overhead** - Direct write to S3 after syntax validation only
- **Lower latency** - ~20ms faster per request on average
- **Higher throughput** - Can handle ~20% more requests/sec without validation layer

#### Developer Experience
- **Simpler API contracts** - No schema version management needed
- **Faster iteration** - Schema changes don't require coordinated updates
- **Less brittle code** - Fewer error paths to maintain
- **Easier onboarding** - New developers don't need to learn schema system

#### Flexibility
- **Accommodates schema evolution** - Works with forward/backward compatible changes
- **No breaking releases** - Deploys don't require coordinated schema updates
- **Supports experimental features** - Can add fields without schema changes

#### Testing
- **Simpler test suite** - Focus on business logic, not schema compliance
- **Less brittle tests** - Don't need comprehensive schema test matrices

### Cons

#### Data Integrity
- **Invalid data enters system** - Malformed or schema-invalid data written to S3
- **Errors detected late** - RDF conversion or downstream consumers fail with cryptic errors
- **Root cause harder** - Can't tell if JSON was valid or schema-invalid at ingestion time
- **Corruption risk** - Invalid entities stored in S3 require cleanup or remediation

#### Operations
- **Post-ingestion cleanup** - Need to detect and handle invalid entities after they're in S3
- **Data quality debt** - Invalid entities accumulate in storage
- **Complex debugging** - Trace issues through pipeline to root cause
- **Support burden** - More "why did this fail?" tickets

#### Schema Management
- **No documentation value** - Schema doesn't document data contract
- **Missing contracts** - External consumers have no formal specification
- **Version coordination** - Implicit contract via existing usage patterns

---

## Option B: Validate Against Schema Before Acceptance

### Pros

#### Data Integrity
- **Catch errors at boundary** - Invalid JSON rejected at API layer
- **Clean guarantees** - Only valid entities enter S3
- **Early error messages** - Clear, actionable feedback to users
- **Root cause obvious** - Validation errors surface immediately at submission
- **No corruption** - Prevents invalid data in S3
- **Schema as documentation** - Explicit data contract

#### Operations
- **Fail fast** - Invalid requests rejected before any storage I/O
- **Lower support burden** - Fewer downstream failures to debug
- **Clean data quality** - No need for cleanup jobs

#### External Integration
- **Clear contracts** - API consumers know exactly what's expected
- **Better compatibility** - Schema integration points are explicit
- **Tooling support** - Code generation, documentation from schema
- **Predictable** - Schema changes are versioned and coordinated

### Cons

#### Performance
- **Validation overhead** - ~10-50ms additional per request for schema validation
- **Higher latency** - All requests pay validation penalty
- **Lower throughput** - ~20% capacity reduction

#### Developer Experience
- **Schema versioning** - Need to coordinate updates across all services
- **Breaking changes** - Schema v2 changes may require migration scripts
- **More error handling** - Validation errors require careful handling and messaging
- **Onboarding overhead** - New developers must learn schema system

#### Flexibility
- **Rigid schema** - Schema changes require coordinated planning
- **Breaking potential** - Schema v1 → v2 may require migrations
- **Experimental features** - Optional fields need schema updates

#### Testing
- **Schema compliance tests** - Need comprehensive test matrices
- **Complex code paths** - Validation, error handling, versioning

#### Schema Management
- **Maintenance burden** - Schemas need versioning, deprecation, migration paths
- **Coordination overhead** - Multiple services must update schemas in sync
- **Deprecation policy** - Need policy for removing fields

---

## Choice

**Selected: Option A (accept any valid JSON)** with background validation.

For **1M+ entities/week scale**, this approach provides optimal API performance while maintaining data quality through asynchronous validation.

### Recommended Approach: Accept Any Valid JSON with Post-Processing Validation

```
1. Accept syntactically valid JSON at API layer (no schema validation)
2. Write to S3 immediately
3. Validate against schema in background job (separate service)
4. Flag invalid entities, log to metrics database, no automatic remediation
5. Report schema drift metrics to inform schema evolution
```

### Key Principles

- **No remediation**: Invalid entities are flagged and logged only
- **No retry**: Failed validations are logged once, no automatic retry
- **Forward only**: Validation status moves pending → valid/invalid, never reverts
- **Cleanup service**: Separate scheduled job marks entities for cleanup after 90 days

### Hybrid Benefits

**Fast API path** - No validation latency in request path
**Data quality** - Background validation catches issues without blocking writes
**Observability** - Metrics track schema compliance over time
**Flexibility** - No schema coordination bottleneck
**Visibility** - Internal API exposes validation status for monitoring

### Implementation Requirements

```yaml
api_layer:
  validation: "syntactic only"
  response_time_target: "<200ms (P99)"
  storage: "immediate"

background_validation:
  service: "schema-validator"
  input: "Kafka entity_published events"
  action: "validate against schema"
  latency: "non-blocking"
  on_invalid: "flag entity, log to metrics, no retry"
  monitoring:
    - schema_compliance_rate
    - invalid_entities_per_day
    - validation_error_types_by_field

cleanup_service:
  service: "validation-cleanup"
  ttl_days: 90
  action: "mark for cleanup, log to metrics"
  monitoring:
    - cleanup_eligible_count
    - cleanup_marked_total
```

---

## Key Decision Factors

| Factor | Option A | Option B |
|--------|----------|----------|
| API latency | 20ms faster | Validation overhead |
| Throughput | ~20% higher | Lower |
| Data integrity | Post-cleanup cleanup | Guaranteed at entry |
| Error visibility | Downstream failures | API-layer rejections |
| Schema documentation | Implicit (from code) | Explicit schema files |
| Maintenance burden | Low (evolves with code) | High (schema versioning) |
| Breaking changes | None | Requires migrations |
| Testing | Business logic | Schema compliance |
| Onboarding overhead | Lower | Higher |

---

## Open Questions

1. **Error threshold**: What percentage of invalid entities is acceptable? (Target: < 1%)
2. **Background validation SLA**: How quickly must schema compliance be verified? (Target: 95% within 24h)
3. **Remediation strategy**: Invalid entities are flagged and logged to metrics database - no automatic remediation
4. **Schema evolution**: How do we notify consumers of schema v2 changes?
5. **Rollback capability**: Can we invalidate S3 snapshots if schema v2 is deployed?

## Implementation Details

For the complete implementation plan, see [POST-PROCESSING-VALIDATION.md](POST-PROCESSING-VALIDATION.md).

This document includes:
- Database schema changes
- Schema validator service architecture
- Cleanup service design
- Metrics and observability strategy
- Deployment approach (observe mode → production)
- Testing strategy
- Schema evolution policy
