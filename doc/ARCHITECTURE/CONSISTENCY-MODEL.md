# Consistency Model and Failure Recovery

## Write atomicity model

The system uses a **two-phase durable write** model with S3 as the system of record.

**Write order (strict):**
1. Write immutable snapshot to S3
2. Insert revision metadata into Vitess
3. Update entity head pointer

S3 success is the definition of a successful revision creation.

## Handling partial failures

### Case: S3 write succeeds, Vitess fails

- Snapshot exists and is immutable
- No visible revision pointer yet
- Snapshot is considered **unpublished**

**Recovery strategy:**
- Periodic reconciler job scans S3 for unpublished snapshots
- Missing Vitess rows are reconstructed from snapshot metadata
- Head pointer is updated if the revision is newer

This makes the system **eventually consistent but never lossy**.

### Case: Vitess insert succeeds, head update fails

- Revision exists but is not visible as head
- Subsequent writes will advance the head correctly

**Recovery strategy:**
- Reconciler verifies:
  - Max revision per entity
  - Head pointer correctness
- Repairs head pointers automatically

---

## Transaction boundaries

Transaction scope:

No distributed transactions

Each step is independently durable

Reconciliation guarantees convergence

This replaces strict ACID with durable, repairable operations.

### Case: S3 succeeds, Vitess fails
- Snapshot exists but is unpublished
- Snapshot remains tagged `publication_state = pending`
- Reconciler scans S3 for pending snapshots
- Missing Vitess rows are recreated from snapshot metadata
- Head pointer is advanced if the revision is newer
- Snapshot tag updated to `published`

### Case: Vitess insert succeeds, head update fails
- Revision metadata exists but is not visible as head
- Reconciler detects head lag
- Head pointer advanced to highest published revision


# Final consistency guarantees
- No data loss (S3 is authoritative)
- Heads never move backward
- History is immutable
- Readers see eventually consistent state
- All inconsistencies are detectable and repairable
- System converges automatically

