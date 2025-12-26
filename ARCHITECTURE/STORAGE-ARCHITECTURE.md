# Storage Architecture

## 3. Storage architecture

### 3.1 S3 – system of record

S3 stores **all entity content**.

- Immutable revision snapshots
- Infinite horizontal scalability
- CDN-friendly
- Cheap long-term storage
- Perfect audit trail
- Immutable revision snapshots
- Versioned buckets
- CDN-backed
- Lifecycle rules for retention

> **A revision is an immutable snapshot stored in S3.**  
> It is written once and never changes.

Consequences:
- No mutable revisions
- No stored diffs
- No page-based state
- No MediaWiki-owned content

Everything else derives from this rule.


Snapshots include S3 tags:
- `publication_state = pending | published`
- `entity_id`
- `revision_id`
- `import_session_id` (optional)

S3 never stores:
- Diffs
- Mutable state
- Indexes

---

### 3.2 Vitess – metadata and indexing only

Vitess stores **pointers and metadata**, never entity content.




## Vitess (index and metadata only)

Vitess stores **pointers**, never entity content.

### Logical tables

```text
entity_head
- entity_id (shard key)
- head_revision_id
- updated_at

entity_revisions
- entity_id (shard key)
- revision_id
- created_at
- author_id
- comment
- snapshot_uri
- content_hash

entity_revision_meta
- entity_id
- revision_id
- size_bytes

entity_delete_audit
- entity_id
- delete_type (soft | hard)
- requested_by
- approved_by
- reason
- timestamp
- retention_expiry
```

```text
entity_head
- entity_id (shard key)
- head_revision_id
- updated_at

entity_revisions
- entity_id (shard key)
- revision_id
- created_at
- author_id
- comment
- snapshot_uri

entity_revision_meta
- entity_id
- revision_id
- size_bytes
- content_hash
```

## Read/Write flow

### Write flow
Write sequence (strict order)

Client
 → API
   → Validate canonical JSON
   → Assign next revision_id
   → Write snapshot to S3 (publication_state = pending)
   → Insert revision metadata into Vitess
   → CAS update entity_head
   → Mark snapshot as published
   → Emit change event

### Read flows

GET /entity/{id}
 → Lookup head_revision_id (Vitess)
 → Fetch snapshot from S3
 → Return JSON

GET /entity/{id}/revision/{revision_id}
 → Fetch snapshot from S3

GET /entity/{id}/history
 → List revisions from Vitess

Backend has zero diff logic.


