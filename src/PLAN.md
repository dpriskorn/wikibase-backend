# Implementation Plan: Entity API Service (MVP)

## Most Essential Component: Entity API Service

**Rationale:** The Entity API is the foundation that validates the entire architecture. It implements the core invariant (immutable S3 snapshots) and exercises all storage layers (S3 + Vitess).

**Validation Strategy:** Per `JSON-VALIDATION-STRATEGY.md`, the API accepts any syntactically valid JSON. Schema validation is deferred to a background service (post-MVP).

## Phase 1: Project Structure & Configuration

```
src/
├── services/
│   ├── entity-api/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── requirements.txt     # Dependencies
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── shared/
│   │   ├── models/              # Pydantic models
│   │   ├── config/             # Configuration
│   │   └── utils/              # Utilities
├── infrastructure/
│   ├── s3_client.py            # SeaweedFS S3 client
│   ├── vitess_client.py         # Vitess MySQL client
│   └── ulid_flake.py          # ID generation
```

## Phase 2: Core Components (In Order)

### 2.1 Configuration Layer
- **File:** `src/services/shared/config/settings.py`
- **Purpose:** Load environment variables (S3, Vitess, logging)
- **Pydantic BaseSettings** for type-safe config

### 2.2 ID Generation Service
- **File:** `src/infrastructure/ulid_flake.py`
- **Purpose:** Generate 64-bit ulid-flake IDs for internal entity IDs
- **Spec:** 1 bit sign + 42 bits timestamp + 21 bits randomness
- **Output:** Python `int` (fits in Vitess BIGINT)
- **Decision:** Python module (not microservice) - simpler, faster, no coordination needed

### 2.3 S3 Client
- **File:** `src/infrastructure/s3_client.py`
- **Purpose:** Read/write immutable snapshots to SeaweedFS
- **Key operations:**
  - `write_snapshot(entity_id, revision_id, data, tags={})`
  - `read_snapshot(entity_id, revision_id)`
  - `mark_published(entity_id, revision_id)`
- **S3 path format:** `{bucket}/{entity_id}/r{revision_id}.json`

### 2.4 Vitess Client
- **File:** `src/infrastructure/vitess_client.py`
- **Purpose:** Metadata and indexing operations
- **Tables to implement:**
  - `entity_head` → `get_head`, `cas_update_head`
  - `entity_revisions` → `insert_revision`, `get_history`
  - `entity_id_mapping` → `register_entity`, `resolve_id`
- **Connection:** MySQL protocol to port 15309

### 2.5 Pydantic Models
- **File:** `src/services/shared/models/entity.py`
- **Purpose:** Request/response models for API parsing
- **Models:**
  - `EntityCreateRequest` - Accepts any valid JSON (using `Dict[str, Any]`)
  - `EntityResponse`
  - `RevisionMetadata`

**Validation:** FastAPI + Pydantic automatically verifies payload is valid JSON. No schema validation at API layer.

## Phase 3: Entity API Service (FastAPI)

### 3.1 Core Write Flow (POST /entity)

```
1. Validate request is syntactically valid JSON
2. Register entity in entity_id_mapping (if new)
3. Get current head_revision_id from entity_head
4. Assign next revision_id = head + 1
5. Write S3 snapshot with tags: publication_state=pending
6. Insert row into entity_revisions
7. CAS update entity_head
8. Mark S3 snapshot as published (update tags)
9. Return EntityResponse with external_id, revision_id
```

### 3.2 Core Read Flow (GET /entity/{id})

```
1. Resolve external_id → internal_id (entity_id_mapping)
2. Get head_revision_id from entity_head
3. Read S3 snapshot: bucket/{external_id}/r{revision_id}.json
4. Return entity data with metadata
```

### 3.3 History Endpoint (GET /entity/{id}/history)

```
1. Resolve external_id → internal_id
2. Query entity_revisions for entity
3. Return list of RevisionMetadata
```

### 3.4 Specific Revision (GET /entity/{id}/revision/{revision_id})

```
1. Read S3 snapshot directly by path
2. Return entity data
```

## Phase 4: Docker Integration

### 4.1 Update docker-compose.yml
Add entity-api service:
```yaml
entity-api:
  build: ./src/services/entity-api
  ports: ["8000:8000"]
  depends_on:
    - seaweedfs
    - vitess
  environment:
    S3_ENDPOINT: http://seaweedfs:8333
    S3_ACCESS_KEY: fakekey
    S3_SECRET_KEY: fakesecret
    S3_BUCKET: testbucket
    VITESS_HOST: vitess
    VITESS_PORT: 15309
```

### 4.2 Health Check Endpoint
- `GET /health` → check S3 + Vitess connectivity
- Return 200 if both healthy

## Phase 5: Testing

### 5.1 Unit Tests
- ID generation (ulid-flake uniqueness)
- JSON parsing validation
- S3 client operations
- Vitess client operations

### 5.2 Integration Tests
- Write entity → verify S3 + Vitess
- Read entity → verify data integrity
- Multiple revisions → verify sequence

### 5.3 Manual Testing
```bash
# Start services
docker-compose up -d

# Create entity
curl -X POST http://localhost:8000/entity \
  -H "Content-Type: application/json" \
  -d @ENTITY-EXAMPLES/Q42.json

# Read entity
curl http://localhost:8000/entity/Q42

# Get history
curl http://localhost:8000/entity/Q42/history
```

## Dependencies

**Python 3.11+**
```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
boto3>=1.29.0
pymysql>=1.1.0
```

## Key Design Decisions

1. **No caching yet** - Follow "avoid premature optimization" principle
2. **No change events yet** - Focus on core CRUD first
3. **Simplified ID mapping** - Use simple table, skip Redis cache
4. **Syntactic validation only** - Accept any valid JSON, no schema validation (per JSON-VALIDATION-STRATEGY.md)
5. **Single service** - Entity API handles all entity operations
6. **Schema validation deferred** - Background service will validate later (post-MVP)
7. **No threat model** - Per OPENCODE-INSTRUCTIONS.md: "everybody is playing nice"

## Success Criteria

1. ✅ Can create an entity via POST /entity
2. ✅ Can read entity via GET /entity/{id}
3. ✅ Can list history via GET /entity/{id}/history
4. ✅ Data persists in SeaweedFS
5. ✅ Metadata persists in Vitess
6. ✅ Immutable snapshots (cannot be modified)
7. ✅ Revision IDs increment monotonically

## Next Steps (After MVP)

1. Implement background schema validation service (consumes change events)
2. Implement change event streaming (Kafka)
3. Add caching layer (Valkey)
4. Implement RDF generation
5. Add bulk operations
6. Implement entity deletion
