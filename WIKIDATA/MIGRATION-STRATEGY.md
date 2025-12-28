# Migration Strategy – MediaWiki/Wikibase to Immutable Revision Backend

This document describes a staged, low-risk migration from the current
MediaWiki/Wikibase revision system to an external backend using immutable
S3 snapshots and Vitess-based indexing.

The strategy prioritizes:
- Data integrity
- Reversibility
- Operational safety
- Minimal downtime

---

## Phase 0 – Preparation

### Goals
- Make the target system production-ready
- Ensure compatibility with existing Wikibase semantics
- Avoid any user-visible changes

### Actions
- Implement the external Wikibase API
- Define canonical JSON normalization for entities
- Define revision ID format and ordering rules
- Set up:
  - S3 buckets (versioned, immutable)
  - Vitess keyspaces and sharding
- Implement MediaWiki backend client (read-only initially)

### Exit criteria
- API passes contract tests
- Sample entities round-trip correctly
- Snapshot hashes are stable and reproducible

---

## Phase 1 – Historical Export

### Goals
- Preserve all existing history
- Build a complete immutable snapshot archive
- Avoid touching production behavior

### Actions
- Iterate over all Wikibase entities
- For each entity:
  - Read all MediaWiki revisions in order
  - Normalize content
  - Write each revision as an immutable S3 snapshot
  - Insert revision metadata into Vitess
- Compute and store content hashes
- Validate revision counts per entity

### Safety properties
- MediaWiki remains the source of truth
- No writes to the new backend from users
- Export is restartable and idempotent

### Exit criteria
- 100% of entities exported
- Revision counts match MediaWiki
- Random spot-check diffs match exactly

---

## Phase 2 – Shadow Reads

### Goals
- Validate read correctness under real traffic
- Compare old and new systems without risk

### Actions
- MediaWiki continues to read from its own database
- In parallel:
  - Fetch the same entity from the new API
  - Compare normalized JSON (async)
- Log mismatches and investigate
- Fix normalization or export bugs

### Safety properties
- User-visible behavior unchanged
- New backend has no production responsibility

### Exit criteria
- Sustained zero-diff parity
- Performance within acceptable bounds

---

## Phase 3 – Read Cutover

### Goals
- Make the new backend authoritative for reads
- Keep writes unchanged

### Actions
- Switch MediaWiki entity reads to the external API
- Keep MediaWiki revision writes enabled
- Continue dual-read comparison for a limited time
- Monitor latency, error rates, and cache behavior

### Safety properties
- Writes still safe in MediaWiki
- Instant rollback possible

### Exit criteria
- Stable read performance
- No correctness regressions
- Operator confidence

---

## Phase 4 – Dual Writes (Time-boxed)

### Goals
- Validate write correctness in the new backend
- Minimize risk window

### Actions
- For each edit:
  - Write to MediaWiki (canonical)
  - Write immutable snapshot to S3
  - Insert revision pointer into Vitess
- Compare revision heads continuously
- Alert on any divergence

### Constraints
- Phase duration must be short
- No new features during this phase

### Exit criteria
- Zero write mismatches
- Stable system behavior

---

## Phase 5 – Write Cutover

### Goals
- Make the new backend the source of truth
- Remove MediaWiki from the write path

### Actions
- Disable MediaWiki revision writes for entities
- Route all entity writes through the external API
- MediaWiki becomes a pure client

### Safety properties
- Rollback still possible via frozen MediaWiki data
- All revisions are immutable and auditable

### Exit criteria
- Successful edits through the new backend
- Correct head tracking
- No data loss incidents

---

## Phase 6 – Decommission Legacy Systems

### Goals
- Reduce operational complexity
- Eliminate scaling bottlenecks

### Actions
- Freeze MediaWiki revision tables
- Disable:
  - RecentChanges for entities
  - Diff cache
  - Watchlist fan-out for structured data
- Replace:
  - RC feeds with an event stream
  - Watchlists with a subscription service

### Exit criteria
- Legacy tables unused
- Operational load reduced
- Clear ownership boundaries

---

## Rollback Strategy

Rollback is possible up to and including Phase 4.

- MediaWiki remains fully intact until Phase 5
- S3 snapshots are append-only and never deleted
- Vitess metadata can be ignored if necessary

After Phase 5, rollback requires re-enabling MediaWiki writes
and replaying snapshots, but no data is lost.

---

## Final State

```text
- All entity content lives in immutable S3 snapshots
- Vitess stores only revision pointers and indexes
- MediaWiki is a client and UI layer
- Diffs are computed on demand
- History is complete, auditable, and scalable
