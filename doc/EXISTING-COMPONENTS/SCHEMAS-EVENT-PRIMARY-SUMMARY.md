# Schemas Event Primary - MediaWiki/Wikibase RDF Change Events

Summary of key schemas from Wikimedia's primary schema repository focusing on MediaWiki change events and Wikibase RDF mutations.

## Overview

The `schemas-event-primary` repository contains JSON schemas for the Wikimedia Event Platform. This document summarizes two key schemas for MediaWiki and Wikibase entity changes:

1. **MediaWiki RecentChange** (`mediawiki/recentchange/1.0.1`)
2. **Wikibase RDF Change** (`mediawiki/wikibase/entity/rdf_change/2.0.0`)

---

## MediaWiki RecentChange Schema

**Schema ID**: `/mediawiki/recentchange/1.0.1`
**Documentation**: [Manual:RCFeed](https://www.mediawiki.org/wiki/Manual:RCFeed)

Represents a MediaWiki RecentChange event for tracking page modifications, categorization, and user actions.

### Core Fields

**Required Fields:**
| Field | Type | Description |
|--------|------|-------------|
| `$schema` | string | URI identifying the JSONSchema |
| `meta` | object | Event metadata |
| `title` | string | Full page name (from `Title::getPrefixedText`) |

**Event Type Field:**
| Field | Type | Description |
|--------|------|-------------|
| `type` | string | Event type: `edit`, `new`, `log`, `categorize`, `external`, or number |
| `bot` | boolean | Flag indicating if change was made by a bot |
| `comment` | string | Edit summary or categorization comment |
| `id` | integer | RC event ID (rcid) |
| `log_action` | string | Action that triggered the event (for log events) |
| `log_id` | integer | ID of related log entry |
| `log_params` | object | Parameters only exists for log events |
| `log_type` | string | Type of log entry |

**Page Change Fields:**
| Field | Type | Description |
|--------|------|-------------|
| `parsedcomment` | string | Comment parsed into HTML |
| `minor` | boolean | Flag indicating if edit was marked as minor |
| `namespace` | integer | Namespace ID of affected page (rc_namespace) |
| `patrolled` | boolean | Flag indicating if change was patrolled |
| `revision` | object | Old and new revision IDs |
| `length` | object | Length of old and new content (new/old) |
| `timestamp` | integer | Unix timestamp derived from rc_timestamp |

**Server/Wiki Metadata:**
| Field | Type | Description |
|--------|------|-------------|
| `server_name` | string | `$wgServerName` |
| `server_script_path` | string | `$wgScriptPath` (typically `/w`) |
| `server_url` | string | `$wgCanonicalServer` |
| `wiki` | string | `wfWikiID` (database prefix + name) |
| `notify_url` | string | URL to view the change diff |

**Meta Object:**
| Field | Type | Description |
|--------|------|-------------|
| `domain` | string | Domain of event or entity |
| `dt` | string | UTC event datetime in ISO-8601 format (system time) |
| `id` | string | UUID for this event instance |
| `offset` | integer | Kafka offset for partition |
| `partition` | integer | Kafka partition |
| `request_id` | string | Unique ID of request that caused event |
| `stream` | string | Stream name (e.g., `mediawiki.recentchange`) |
| `topic` | string | Kafka topic with datacenter prefix |
| `uri` | string | Unique URI identifying event or entity |

### Event Types

| Type | Description |
|------|-------------|
| `edit` | Page was edited |
| `new` | New page created |
| `log` | Special log action recorded |
| `categorize` | Page was added to category |
| `external` | External change (from another system) |
| `<number>` | Numeric event type for other actions |

### Constraints

- **Namespace ID Range**: -9,007,199,254,740,991 to 9,007,199,254,740,991 (unsigned 64-bit)
- **Timestamp Range**: -9,007,199,254,740,991 to 9,007,199,254,740,991 (Unix timestamp)
- **Revision IDs**: Can be `null` for new pages
- **Comment HTML**: May contain parsed HTML markup

---

## Wikibase RDF Change Schema

**Schema ID**: `/mediawiki/wikibase/entity/rdf_change/2.0.0`

Represents a change to a Wikibase entity's RDF representation in a triple store (e.g., Blazegraph). This schema enables streaming updates to keep the RDF graph synchronized with MediaWiki/Wikibase changes.

### Purpose

Keeps a Wikibase instance's RDF graph up-to-date without requiring external API calls. Contains all necessary RDF triples to reconstruct the entity's current state.

### Core Fields

**Required Fields:**
| Field | Type | Description |
|--------|------|-------------|
| `$schema` | string | URI identifying the JSONSchema |
| `dt` | string | ISO-8601 formatted UTC timestamp when event occurred |
| `entity_id` | string | Wikibase entity ID being modified |
| `meta` | object | Event metadata |
| `operation` | string | Type of update performed |
| `rev_id` | integer | Database revision ID (max: 9007199254740991, min: 0) |
| `sequence` | integer | Sequence number for event reconstruction |
| `sequence_length` | integer | Number of chunks in multi-part message |

**Meta Object:**
| Field | Type | Description |
|--------|------|-------------|
| `domain` | string | Domain of event or entity (e.g., `www.wikidata.org`) |
| `dt` | string | Time when system received the event (UTC ISO-8601) |
| `id` | string | UUID for this event |
| `request_id` | string | Unique ID of request that caused event |
| `stream` | string | Stream name (dataset) this event belongs to |
| `uri` | string | Unique URI identifying event or entity |

### Operation Types

| Operation | Description | RDF Fields Populated |
|-----------|-------------|------------------------|
| `diff` | All fields populated. Used for new revisions (import) or edits (changes) |
| `import` | `rdf_added_data` and `rdf_linked_shared_data` populated. Used for entity creation or restoration |
| `delete` | Only metadata fields populated (`entity_id`, `rev_id`). Consumer must delete all triples for the entity |
| `reconcile` | Only `rdf_added_data` populated. Indicates prior inconsistencies detected; consumer must perform full reconciliation |

### RDF Data Fields

**RDF Format**: Encoded as Turtle (`text/turtle`)

| Field | Type | Description | Used By |
|--------|------|-------------|---------|
| `rdf_added_data` | object | Triples that **must be added** | `diff`, `import`, `reconcile` |
| `rdf_deleted_data` | object | Triples that **must be deleted** | `diff` (consumer must know existing triples) |
| `rdf_linked_shared_data` | object | Triples that might be shared by other entities (could be added) | `diff`, `import`, `reconcile` |
| `rdf_unlinked_shared_data` | object | Triples used by other entities but no longer linked from this entity | Consumer decides whether to keep or delete |

**RDF Data Object Structure:**
```yaml
rdf_added_data:
  type object
  additionalProperties false
  required:
    - mime_type
    - data
  properties:
    mime_type:
      description: Mime type of RDF data
      type: string
    data:
      description: RDF data encoded using mime_type
      type: string

rdf_deleted_data:
  type object
  additionalProperties false
  required:
    - mime_type
    - data
  properties:
    mime_type:
      description: Mime type of RDF data
      type: string
    data:
      description: RDF data encoded using mime_type
      type: string
```

**MIME Types:**
- `text/turtle` - Turtle format RDF data
- `application/n-triples` - N-Triples format
- `application/rdf+xml` - RDF/XML format

### RDF Content Characteristics

**Omitted for Performance:**
- No `rdf:type` statements
- No `wdata:` nodes (use of blank nodes discouraged by WDQS)
- Only `rdfs:label` present (schema:name & skos:prefLabel omitted)
- SomeValues encoded as blank nodes with skolemization

**Triple Categories:**
| Category | Description | Consumer Behavior |
|-----------|-------------|-------------------|
| **Added triples** | Must be added to the graph |
| **Deleted triples** | Must be removed from the graph |
| **Linked shared** | May be added (might already exist) |
| **Unlinked shared** | May create orphans if kept (orphaned triples) |
| **Reconciled triples** | Only for `reconcile` operations |

### Message Chunking

For large RDF payloads, events may be split across multiple consecutive messages:

| Field | Description |
|--------|-------------|
| `sequence` | Index of chunk (starts at 0) |
| `sequence_length` | Number of chunks in event |
| `meta.request_id` | Used to group chunks and verify consistency |

**Reconstruction Rules:**
- Chunks for same event appear consecutively in stream
- Consumer reconstructs by parsing all `rdf_*_data` fields
- Append statements to build complete RDF graph
- Use `meta.request_id` to group related messages
- Buffering condition: `sequence + 1 == sequence_length`

### Message Ordering

**Guaranteed:**
- Two consecutive edits on same entity appear in right order

**Not Guaranteed:**
- Two consecutive edits on different entities are not guaranteed same order

This is generally not a problem but may pose challenges for sitelinks which are modeled as a separate "well identified" subject. The entity may be updated before the consumer processes a sitelink event, causing the sitelink to point to a non-existent entity.

---

## Comparison of Schemas

| Aspect | RecentChange | RDF Change |
|---------|--------------|-----------|
| **Purpose** | Track page edits, categorization | Keep RDF graph synchronized |
| **Granularity** | Individual edit events | Entity-level RDF state |
| **Data Format** | MediaWiki-specific fields | RDF triples (Turtle) |
| **Payload Size** | Typically small | Can be very large (supports chunking) |
| **Consumers** | RC feeds, analytics, monitoring | WDQS Streaming Updater Consumer |
| **Update Model** | Diff between revisions | Complete RDF state |
| **Schema Version** | 1.0.1 | 2.0.0 |
| **Stream Name** | `mediawiki.recentchange` | Various (per wiki/entity) |

---

## Common Patterns

Both schemas follow Event Platform guidelines:

1. **Required Fields**: `$schema`, `meta` (with `stream`, `dt`, `id`, `domain`, `uri`)
2. **Timestamps**: ISO-8601 UTC with `_dt` suffix and `maxLength: 128`
3. **Identifiers**: Snake case, no special characters
4. **Metadata**: `meta.dt` for system time, `dt` for event time
5. **UUIDs**: For unique event identification and request tracking
6. **Backwards Compatibility**: Only add new optional fields

## Usage Examples

### RecentChange Example
```json
{
  "$schema": "/mediawiki/recentchange/1.0.1",
  "type": "edit",
  "title": "My Article",
  "bot": false,
  "comment": "Fixed typos",
  "namespace": 0,
  "revision": {
    "new": 123456,
    "old": 123455
  },
  "timestamp": 1703075200,
  "user": "ExampleUser",
  "wiki": "enwiki",
  "meta": {
    "stream": "mediawiki.recentchange",
    "dt": "2023-12-20T10:30:00Z",
    "id": "550e8400-4eac-4262-a451-b7ca247e401c",
    "domain": "en.wikipedia.org"
  }
}
```

### RDF Change Example
```json
{
  "$schema": "/mediawiki/wikibase/entity/rdf_change/2.0.0",
  "dt": "2023-12-20T10:30:00Z",
  "entity_id": "Q42",
  "operation": "diff",
  "rev_id": 1234567890,
  "sequence": 0,
  "sequence_length": 1,
  "meta": {
    "stream": "wdqs.wikidata.mutation",
    "dt": "2023-12-20T10:30:05Z",
    "id": "abc123-def456-7890-abc123-def456-7890",
    "domain": "www.wikidata.org",
    "request_id": "req-987654321",
    "stream": "wikidata-mutation-stream"
  },
  "rdf_added_data": {
    "mime_type": "text/turtle",
    "data": "<http://www.wikidata.org/entity/Q42> a:Statement a:Property <http://www.wikidata.org/property/P31> 'Douglas Adams'; <http://www.wikidata.org/prop/statement/value/P31> 'Douglas Adams' ."
  },
  "rdf_deleted_data": {
    "mime_type": "text/turtle",
    "data": "<http://www.wikidata.org/entity/Q42> a:Statement a:Property <http://www.wikidata.org/property/P31> 'Previous name' ."
  },
  "rdf_linked_shared_data": {
    "mime_type": "text/turtle",
    "data": "<http://www.wikidata.org/prop/direct/P31> a:owl:equivalentProperty <http://www.wikidata.org/prop/direct/P2295> 'creator of' ."
  }
}
```

## References

- [MediaWiki RCFeed Manual](https://www.mediawiki.org/wiki/Manual:RCFeed)
- [Wikidata Query Service Streaming Updater](https://wikitech.wikimedia.org/wiki/Wikidata_query_service/Streaming_Updater)
- [Wikibase RDF Dump Format](https://www.mediawiki.org/wiki/Wikibase/Indexing/RDF_Dump_Format)
- [Event Platform Schema Guidelines](EVENT-PLATFORM-SCHEMA-GUIDELINES.md)
- [Primary Schema Repository](https://gitlab.wikimedia.org/repos/data-engineering/schemas-event-primary)
