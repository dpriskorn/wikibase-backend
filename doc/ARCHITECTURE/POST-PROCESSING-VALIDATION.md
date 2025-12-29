# Post-Processing Validation Strategy

## Overview

This document describes the background validation service architecture for Wikibase, implementing Option A from JSON-VALIDATION-STRATEGY.md: accept any syntactically valid JSON at the API layer, then validate against schema asynchronously in a background service.

## Core Principles

1. **Fast API Path**: No validation latency in the request path - accept any syntactically valid JSON
2. **Background Validation**: Schema validation happens asynchronously via separate service
3. **No Remediation**: Invalid entities are flagged and logged, never automatically modified or deleted
4. **No Retry**: Failed validations are logged once, no automatic retry logic
5. **Forward Only**: Validation status moves from pending → valid/invalid, never back to pending
6. **Metrics-First**: All validation results logged to metrics database for analysis

## Architecture

### Data Flow

```
┌─────────────┐
│  API Layer  │ Accepts any valid JSON
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────────┐
│     S3      │────▶│  Change Events   │ (Kafka)
│ (Snapshots) │     └────────┬─────────┘
└─────────────┘              │
                             ▼
                  ┌──────────────────────┐
                  │  Schema Validator    │
                  │  (Background Service) │
                  └──────────┬───────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
         ┌─────────────┐         ┌──────────────┐
         │  Vitess DB  │         │ Metrics DB   │
         │   (metadata)│         │ (time-series) │
         └─────────────┘         └──────────────┘
                │
                ▼
         ┌──────────────┐
         │ Cleanup      │ (Scheduled Job)
         │ Service      │
         └──────────────┘
```

## Phase 1: Storage Schema

### 1.1 Database Schema Changes

#### entity_revision_meta Table

Add validation metadata to track per-revision validation state:

```sql
ALTER TABLE entity_revision_meta ADD COLUMN
  validation_status ENUM('pending', 'valid', 'invalid') DEFAULT 'pending',
  validation_error TEXT DEFAULT NULL,
  validated_at TIMESTAMP DEFAULT NULL,
  schema_version VARCHAR(20) DEFAULT NULL,
  INDEX idx_validation_status (validation_status, validated_at);
```

**Fields**:
- `validation_status`: Current state of validation for this revision
  - `pending`: Not yet validated
  - `valid`: Passed schema validation
  - `invalid`: Failed schema validation
- `validation_error`: JSON string with detailed error information
- `validated_at`: Timestamp when validation completed
- `schema_version`: Schema version used for validation

### 1.2 Metrics Database Schema

```sql
CREATE TABLE validation_metrics (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  entity_id VARCHAR(50) NOT NULL,
  revision_id BIGINT NOT NULL,
  validation_status VARCHAR(20) NOT NULL,
  error_category VARCHAR(50),
  error_message TEXT,
  schema_version VARCHAR(20),
  validated_at TIMESTAMP NOT NULL,
  processing_time_ms INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_entity_revision (entity_id, revision_id),
  INDEX idx_validated_at (validated_at),
  INDEX idx_error_category (error_category)
) ENGINE=InnoDB;
```

### 1.3 Schema Definition

Create canonical JSON schema file:

**File**: `schemas/entity.schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://wikibase.org/schemas/entity.json",
  "title": "Wikibase Entity",
  "version": "1.0",
  "type": "object",
  "required": ["entity_id", "entity_type", "schema_version"],
  "properties": {
    "entity_id": {
      "type": "string",
      "pattern": "^[A-Za-z][0-9]+$"
    },
    "entity_type": {
      "type": "string",
      "enum": ["item", "property", "lexeme"]
    },
    "schema_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$"
    },
    "labels": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["language", "value"],
        "properties": {
          "language": {"type": "string"},
          "value": {"type": "string"}
        }
      }
    },
    "descriptions": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["language", "value"],
        "properties": {
          "language": {"type": "string"},
          "value": {"type": "string"}
        }
      }
    },
    "claims": {
      "type": "object",
      "additionalProperties": {
        "type": "array"
      }
    },
    "sitelinks": {
      "type": "object"
    }
  }
}
```

## Phase 2: Schema Validator Service

### 2.1 Service Architecture

**Service Name**: `schema-validator`

**Responsibilities**:
- Consume entity publication events from Kafka
- Fetch entity snapshots from S3
- Validate against canonical JSON schema
- Update `entity_revision_meta` with validation status
- Log all results to metrics database
- Emit validation completion events (optional)

### 2.2 Input Events

Consume from Kafka topic: `wikibase.entity_published`

```json
{
  "entity_id": "Q123",
  "revision_id": 42,
  "snapshot_uri": "s3://wikibase-revisions/Q123/r0000000042.json",
  "timestamp": "2025-01-15T10:30:00Z",
  "author_id": "user123"
}
```

### 2.3 Validation Pipeline

```
1. Consume entity_published event
   ↓
2. Fetch snapshot from S3
   ↓
3. Parse JSON (syntactic validation already done at API layer)
   ↓
4. Validate against entity.schema.json
   ↓
5. Classify validation result
   - Valid: status = 'valid'
   - Invalid: status = 'invalid', capture error details
   ↓
6. Update entity_revision_meta
   UPDATE entity_revision_meta
   SET validation_status = ?,
       validation_error = ?,
       validated_at = NOW(),
       schema_version = ?
   WHERE entity_id = ? AND revision_id = ?
   ↓
7. Log to metrics database
   INSERT INTO validation_metrics (...)
   ↓
8. Emit validation_completed event (optional)
```

### 2.4 Error Classification

No automatic retries - all errors are logged once.

| Error Type | Category | Severity | Action |
|------------|----------|----------|--------|
| Missing required field | `schema_violation` | high | Log to metrics, mark invalid |
| Invalid field type | `schema_violation` | high | Log to metrics, mark invalid |
| Invalid value format | `schema_violation` | high | Log to metrics, mark invalid |
| Unknown field | `extra_field` | info | Log to metrics, mark valid (forward compatible) |
| Schema version mismatch | `schema_version_error` | medium | Log to metrics, mark invalid |

**Error Response Format**:

```json
{
  "validation_status": "invalid",
  "error_category": "schema_violation",
  "errors": [
    {
      "field": "/labels",
      "message": "Required property missing",
      "pointer": "#/labels"
    },
    {
      "field": "/claims/P31/0",
      "message": "Invalid datatype: expected string, got number",
      "pointer": "#/claims/P31/0/datavalue/value"
    }
  ]
}
```

### 2.5 Configuration

```yaml
service:
  name: "schema-validator"
  version: "1.0.0"

input:
  kafka_topic: "wikibase.entity_published"
  consumer_group: "schema-validator-group"
  poll_timeout_ms: 1000

processing:
  parallel_workers: 50
  batch_size: 100
  validation_timeout_ms: 5000

storage:
  s3_bucket: "wikibase-revisions"
  vitess_database: "wikibase"

schema:
  schema_file: "/schemas/entity.schema.json"
  current_version: "1.0"

metrics:
  database: "metrics_db"
  write_interval_seconds: 10

cleanup:
  ttl_days: 90
  check_interval_hours: 24
```

### 2.6 Technology Stack

- **Language**: Python or Go (recommended for JSON processing)
- **JSON Schema Library**: `jsonschema` (Python) or `gojsonschema` (Go)
- **Kafka Client**: `confluent-kafka-python` or `github.com/IBM/sarama`
- **S3 Client**: AWS SDK
- **Vitess Client**: MySQL-compatible driver

## Phase 3: Cleanup Service

### 3.1 Service Architecture

**Service Name**: `validation-cleanup`

**Responsibilities**:
- Periodically scan for entities with `validation_status = 'invalid'`
- Check if entities are eligible for cleanup (age > 90 days, not in head)
- Log cleanup actions to metrics database
- Record deletions in audit table

### 3.2 Cleanup Criteria

An entity is eligible for cleanup when ALL of the following are true:

1. `validation_status = 'invalid'` in `entity_revision_meta`
2. `validated_at < NOW() - INTERVAL 90 DAY`
3. `revision_id != head_revision_id` in `entity_head` (entity has newer valid revision)
4. No active references from other entities (optional, future enhancement)

### 3.3 Cleanup Process

```
1. Scheduled job runs (daily)
   ↓
2. Query for cleanup candidates
   SELECT er.entity_id, er.revision_id, er.snapshot_uri
   FROM entity_revision_meta er
   JOIN entity_head eh ON er.entity_id = eh.entity_id
   WHERE er.validation_status = 'invalid'
     AND er.validated_at < NOW() - INTERVAL 90 DAY
     AND er.revision_id < eh.head_revision_id
   ↓
3. For each candidate:
   - Log to validation_metrics with action = 'marked_for_cleanup'
   - Update entity_revision_meta.validation_status = 'cleanup_eligible'
   - Optionally: Record in entity_delete_audit table
   ↓
4. Emit cleanup_eligible event for downstream systems
   ↓
5. (Optional) Physical deletion of S3 snapshots in separate job
```

**Note**: This service only MARKS entities for cleanup and logs to metrics. Actual S3 deletion is a separate manual or automated process.

### 3.4 Cleanup Event Format

```json
{
  "event_type": "cleanup_eligible",
  "entity_id": "Q123",
  "revision_id": 42,
  "snapshot_uri": "s3://wikibase-revisions/Q123/r0000000042.json",
  "validated_at": "2024-09-26T10:30:00Z",
  "validation_error": "...",
  "reason": "Invalid revision older than 90 days with newer valid revision"
}
```

## Phase 4: Metrics & Observability

### 4.1 Key Metrics

#### Validation Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `validation_total` | counter | Total number of validations |
| `validation_success_total` | counter | Total passed validations |
| `validation_failed_total` | counter | Total failed validations |
| `validation_success_rate` | gauge | (success / total) * 100 |
| `validation_latency_seconds` | histogram | Validation processing time |
| `validation_backlog_size` | gauge | Number of pending validations |

#### Error Metrics

| Metric Name | Labels | Description |
|-------------|--------|-------------|
| `validation_errors_total` | category | Errors by category |
| `validation_errors_by_field` | field_name | Errors by JSON field |

#### Cleanup Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `cleanup_marked_total` | counter | Entities marked for cleanup |
| `cleanup_eligible_count` | gauge | Current eligible count |

### 4.2 Alerting Rules

```yaml
alerts:
  - name: HighValidationErrorRate
    condition: validation_error_rate > 1%
    severity: critical
    description: "More than 1% of validations failing"

  - name: ValidationBacklogGrowing
    condition: validation_backlog_size > 100000 AND increasing
    severity: warning
    description: "Validation backlog growing beyond threshold"

  - name: CleanupBacklogGrowing
    condition: cleanup_eligible_count > 10000
    severity: info
    description: "Large number of entities eligible for cleanup"
```

### 4.3 Dashboard Requirements

**Grafana Dashboard: Wikibase Validation**

- Panel 1: Validation status distribution (pie chart)
- Panel 2: Validation success rate over time (line chart)
- Panel 3: Error breakdown by category (bar chart)
- Panel 4: Validation latency P50/P95/P99 (heatmap)
- Panel 5: Validation backlog size (gauge)
- Panel 6: Cleanup eligible entities (gauge)
- Panel 7: Error rate by field (table)
- Panel 8: Top 10 entities with validation errors (table)

### 4.4 API Visibility

**Internal API Endpoints** (not exposed to end users):

```
GET /internal/validation/metrics
  → Returns aggregated validation metrics
  Response:
  {
    "total_validations": 1000000,
    "success_rate": 99.2,
    "error_rate": 0.8,
    "backlog_size": 500,
    "error_breakdown": {
      "schema_violation": 5000,
      "extra_field": 2000,
      "schema_version_error": 1000
    }
  }

GET /internal/validation/entity/{entity_id}
  → Returns validation status for specific entity
  Response:
  {
    "entity_id": "Q123",
    "head_revision_id": 42,
    "validation_status": "invalid",
    "validation_error": "...",
    "validated_at": "2025-01-15T10:30:00Z"
  }

GET /internal/validation/errors
  → Returns list of validation errors (paginated)
  Query params: status, category, limit, offset
```

## Phase 5: Deployment Strategy

### 5.1 Observe Mode (Weeks 1-2)

**Purpose**: Validate metrics and processing behavior before enabling writes.

**Configuration**:
- Consume Kafka events and fetch S3 snapshots
- Validate against schema
- Log to metrics database only
- **DO NOT** update `entity_revision_meta` table
- Monitor validation success rate, error patterns, processing time

**Monitoring Focus**:
- What is the actual validation error rate?
- Which fields cause the most errors?
- What is the processing time distribution?
- Are there performance bottlenecks?

**Decision Points**:
- Adjust `parallel_workers` based on throughput
- Adjust `poll_interval` based on backlog growth
- Refine error categories based on observed patterns

### 5.2 Production Rollout (Week 3)

**Step 1**: Enable writes to `entity_revision_meta`
- Deploy service update
- Monitor `validation_backlog_size` drains

**Step 2**: Deploy cleanup service
- Configure TTL = 90 days
- Monitor cleanup eligibility metrics

**Step 3**: Set up Grafana dashboards and alerts
- Configure alert thresholds
- Add on-call rotation for alerts

### 5.3 Rollback Plan

If critical issues are detected:

1. Stop schema-validator service (stops new validations)
2. Revert API visibility endpoints to return "unknown"
3. Keep metrics database logging for post-mortem analysis
4. Delete/update rows in `entity_revision_meta` if needed

## Phase 6: Testing Strategy

### 6.1 Unit Tests

- Test each validation rule independently
- Test error classification logic
- Test metrics database queries
- Test cleanup eligibility logic

### 6.2 Integration Tests

- Test end-to-end flow: Kafka → S3 → Vitess → Metrics DB
- Test with valid entities from `ENTITY-EXAMPLE-Q42.json`
- Test with invalid entities (missing fields, wrong types)
- Test cleanup service queries and eligibility checks

### 6.3 Performance Tests

- Validate 1000 entities in < 5 minutes
- Measure throughput with different `parallel_workers` settings
- Test memory usage with large entities (>500 claims)

### 6.4 Test Data

Create test entity files:
- `tests/data/valid-basic.json` - Simple valid entity
- `tests/data/valid-complex.json` - Entity with many claims
- `tests/data/invalid-missing-field.json`
- `tests/data/invalid-wrong-type.json`
- `tests/data/invalid-schema-version.json`

## Phase 7: Schema Evolution

### 7.1 Schema Versioning Policy

Follow [S3-REVISION-SCHEMA-EVOLUTION.md](S3-REVISION-SCHEMA-EVOLUTION.md):

- **MAJOR** versions (1.0 → 2.0): Breaking changes
  - Require all consumers to upgrade before deployment
  - Update `schema_version` field in snapshots
  - Validator must support both versions during transition

- **MINOR** versions (1.0 → 1.1): Backward-compatible additions
  - Add optional fields
  - Existing valid entities remain valid
  - Deploy new schema, upgrade validator

### 7.2 Validation Service Schema Support

- Validator must support N-1 schema versions (current + previous major)
- Read `schema_version` from snapshot
- Validate against appropriate schema version
- Log `schema_version` to metrics database

### 7.3 Schema Drift Monitoring

Track schema compliance over time:

```sql
SELECT
  schema_version,
  COUNT(*) as total,
  SUM(CASE WHEN validation_status = 'valid' THEN 1 ELSE 0 END) as valid_count,
  SUM(CASE WHEN validation_status = 'invalid' THEN 1 ELSE 0 END) as invalid_count,
  (SUM(CASE WHEN validation_status = 'valid' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as success_rate
FROM validation_metrics
WHERE validated_at >= NOW() - INTERVAL 7 DAY
GROUP BY schema_version;
```

## Phase 8: Documentation

### 8.1 Required Documentation

1. **API Documentation**
   - Internal API endpoint specifications
   - Example requests/responses
   - Error codes and handling

2. **Operations Runbook**
   - Service deployment procedures
   - Alert troubleshooting guide
   - Rollback procedures
   - Performance tuning guidelines

3. **Schema Documentation**
   - Current schema version and changes
   - Field descriptions and constraints
   - Migration guides for schema updates

### 8.2 Onboarding Checklist

- [ ] Schema version 1.0 defined and documented
- [ ] Internal API endpoints implemented and tested
- [ ] Grafana dashboard configured
- [ ] Prometheus alerts configured
- [ ] Ops team trained on alert response
- [ ] Rollback procedures documented
- [ ] Schema evolution process documented

## Open Questions

1. **Schema Definition**: Should the JSON schema be based on existing Wikidata entity examples (`ENTITY-EXAMPLE-Q42.json`, `ENTITY-EXAMPLE-Q45648994.json`)?

2. **Initial Backfill**: When the validation service is first deployed, should it validate all existing historical entities, or only new entities going forward?

3. **Metrics Database Choice**: Which database should be used for metrics? (TimescaleDB, InfluxDB, Prometheus, etc.)

4. **Cleanup Action**: Should the cleanup service only MARK entities for cleanup, or actually delete S3 snapshots?

5. **Parallelism**: How many workers should be deployed for the schema validator? (Recommendation: Start with 10, scale based on observed throughput)

6. **Polling Interval**: What is the target time between entity publication and validation completion? (Recommendation: < 1 hour for initial deployment)

## References

- [JSON-VALIDATION-STRATEGY.md](JSON-VALIDATION-STRATEGY.md) - Overall validation strategy and Option A rationale
- [S3-REVISION-SCHEMA-EVOLUTION.md](S3-REVISION-SCHEMA-EVOLUTION.md) - Schema versioning and migration policy
- [STORAGE-ARCHITECTURE.md](STORAGE-ARCHITECTURE.md) - S3 and Vitess storage design
- [CHANGE-NOTIFICATION.md](CHANGE-NOTIFICATION.md) - Event streaming and Kafka topics
- [ENTITY-MODEL.md](ENTITY-MODEL.md) - Entity examples and structure
