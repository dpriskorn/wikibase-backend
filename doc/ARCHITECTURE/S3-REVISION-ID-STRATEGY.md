# Revision ID Strategy

## Chosen approach: **Monotonic per-entity revision IDs**

**Format:**

(entity_id, revision_number)

Example:

Q123:r0000000042

## Rationale

- Simple ordering
- No collision handling
- Efficient CAS operations
- Content-hash can still be stored for deduplication checks

Content hashes are stored as metadata, not identifiers.
