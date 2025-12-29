# Event Platform Schema Guidelines

Summary of conventions, rules, and guidelines for designing and evolving Wikimedia Event Platform schemas.

## Overview

This document provides the official guidelines for creating and maintaining JSON schemas used across Wikimedia's Event Platform. Schemas define the structure of events flowing through Kafka and are consumed by downstream systems like analytics pipelines, search indexing, and cache purging.

**Schema Repositories:**
- **Primary**: [schemas/event/primary](https://gitlab.wikimedia.org/repos/data-engineering/schemas-event-primary) - Critical production systems
- **Secondary**: [schemas/event/secondary](https://gitlab.wikimedia.org/repos/data-engineering/schemas-event-secondary) - Less critical/development schemas

## Required Fields

Every event schema MUST include these fields:

### `$schema`
- **Type**: URI (string)
- **Purpose**: Identifies the JSON Schema for this event
- **Format**: Matches schema repository $id field
- **Example**: `/schema_name/1.0.0`

### `meta`
- **Type**: object
- **Purpose**: Event metadata common to all events
- **Required**: Contains routing and tracking information

### `meta.stream`
- **Type**: string
- **Purpose**: Name of stream/queue (routes events to Kafka topics/Hive tables)
- **Format**: Lowercase snake_case
- **Example**: `mediawiki.page_change.v1`

### `meta.dt`
- **Type**: string (ISO-8601 datetime)
- **Purpose**: Event ingestion/processing time (server-side timestamp)
- **Set by**: EventGate or producer library
- **Format**: `2015-12-20T09:10:56Z`
- **Note**: Leave blank in event data; let EventGate set it

### `dt`
- **Type**: string (ISO-8601 datetime)
- **Purpose**: Event occurrence time (when the event actually happened)
- **Format**: `2015-12-20T09:10:56Z`
- **Set by**: Client/producer

**Timestamp Guidelines:**
- Use `_dt` suffix for datetime fields
- Always use UTC timezone (append `Z`)
- Specify `maxLength: 128` for format validation
- Use ISO-8601 format: `YYYY-MM-DDTHH:MM:SSZ`

## Rules

### 1. No Union Types / No Null Values

**Union types are forbidden:**
```yaml
# NOT ALLOWED
type: [string, integer]
type: [string, null]
```

**Allowed use of oneOf** (only for validation, not variable types):
```yaml
# NOT ALLOWED
oneOf:
  - type: object
    properties:
      f1:
        type string
  - type: object
    properties:
      f1:
        type integer
```

**Optional fields**: Simply omit the field if not set. Missing fields become `NULL` in SQL systems.

### 2. No Object additionalProperties

**Full structure must be known** - use explicit properties for objects.

**Exception**: Map types (use `additionalProperties` for maps)

### 3. Arrays

**Must specify items type** - all items must have same type:

```yaml
links_hovered:
  type: array
  items:
    type: object
    properties:
      link_url:
        type string
      hover_time_ms:
        type integer
```

**Complex array elements** are discouraged for evolution reasons (see below).

### 4. Identifier Naming Rules

#### No Capital Letters - Use snake_case

All identifiers (schema names, field names) MUST be lowercase snake_case.

**Reason**: Events are imported into case-insensitive SQL systems. Mixed case causes confusion.

**Exception**: Map keys may use mixed case (but prefer lowercase).

#### No Special Characters

Avoid characters requiring SQL quoting: hyphens `-`, spaces ` `, `@`, etc.

#### Acceptable Identifier Regex

```
/^[$a-z]+[a-z0-9_]*$/
```

**Note**: Dollar sign `$` is reserved for JSONSchema's `$schema` field.

### 5. Backwards Compatible Modifications Only

**Only allowed change**: Adding new optional fields.

#### No Type Changes
- Type changes are the most destructive backwards-incompatible change
- Can severely break downstream consumers

#### Do Not Remove Fields
- Removal causes downstream failures
- Best practice: never remove fields

#### Do Not Rename Fields
- Renaming = remove + add, which is not allowed

#### Do Not Delete Schemas
- Even if producer no longer emits events
- Data may exist in storage/queues
- Schema must remain for data mapping

### Exceptions to Backwards Compatibility

#### Major Schema Version Upgrades
- Allowed between major versions (per semver)
- Tooling does NOT support automatic migration
- Requires manual migration for ALL producers/consumers
- Coordinate with all data users before implementing

#### Incompatible Changes to Unused Schemas
- If schema has no production stream declared: incompatible changes are fine
- No producers/consumers to migrate
- Edit `current.yaml` directly (don't change version)

#### Incompatible Changes to WMF Analytics Schemas
- If ONLY consumed by analytics (Hive tables)
- Data Engineering can assist with manual table drops/alters
- Review schema change with Data Engineering team

## Conventions

### Optional / Missing Fields

- Non-required fields are optional
- Omit field if value not set (don't use `null`)
- Missing fields become `NULL` in SQL during ingestion

### Examples

- **Include at least one example** in schema
- Used for canary/heartbeat events for monitoring
- jsonschema-tools generates random examples if not provided
- Prefer custom examples over auto-generated

```yaml
examples:
  - $schema: /test/event/1.0.0
    meta:
      stream: test_stream
      dt: 2023-01-01T00:00:00Z
    dt: 2023-01-01T00:00:00Z
    test_field: test_value
```

### Datetimes

**Naming conventions:**
- `_dt` suffix: ISO-8601 string datetime
- `_ts_ms` suffix: Unix timestamp (milliseconds)
- `_ts_s` suffix: Unix timestamp (seconds)

```yaml
session_start_dt:
  type string
  format date-time
  maxLength 128

session_start_ts_ms:
  type integer
  description Session start time as millisecond Unix timestamp
```

**Format requirements:**
- ISO-8601 with UTC `Z` suffix: `2015-12-20T09:10:56Z`
- Always include `maxLength: 128` (security constraint)

### Elapsed Time Fields

Use integer milliseconds with explicit time unit suffix:

```yaml
page_preview_visible_time_ms:
  type integer
  description Time the page preview popup was shown to user

api_response_time_ns:
  type integer
  description API response time in nanoseconds
```

**Time unit suffixes:**
- `_ms` - milliseconds
- `_ns` - nanoseconds
- `_s` - seconds

### Map Types

Use maps when field names are unknown ahead of time.

**Simple string map:**
```yaml
map_field:
  type object
  additionalProperties:
    type string
```

**Complex value type:**
```yaml
map_field:
  type object
  additionalProperties:
    type object
    properties:
      p1:
        type string
      p2:
        type integer
```

#### Declaring Specific Fields in Maps

Add validation for specific map keys:

```yaml
map_field:
  type object
  additionalProperties:
    type string
  properties:
    phone_number:
      type string
      format '^\+\d{1,2}\s?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}$'
```

**WARNING**: Do NOT mix strings and `format: date-time` in same map. Event Platform converts date-time strings to DateTime types.

#### Complex Array/Map Evolution Warning

**Complex types in arrays/maps are NOT well supported for evolution.**
- SQL DDL (Spark, Hive) cannot alter nested struct types
- Once a complex type is used, you CANNOT add fields to it
- Prefer flat structures or simple types for evolvable schemas

See [T366487](https://phabricator.wikimedia.org/T366487).

### Modeling State Changes

Model state by providing **both current and previous state** rather than diffs.

```yaml
blocks:
  description Current state of blocks
  type object
  properties:
    name:
      type boolean
    email:
      type boolean

prior_state:
  description Prior state before this event
  type object
  properties:
    name:
      type boolean
    email:
      type boolean
```

**Rules:**
- Current state: Top-level event body
- Previous state: `prior_state` subobject with same fields
- If field not in `prior_state`: value hasn't changed

### Schema Fragments

Use fragments for reusable schema components.

**Fragment guidelines:**
- Events should NEVER use fragment as `$schema` URI
- Concrete schemas should only `$ref` `fragment/` schemas
- Avoid `required` fields in fragment schemas (let concrete schemas decide)
- Fragments in `fragment/` namespace only

**Best practice:**
```yaml
allOf:
  - $ref /fragment/common/2.0.0#
properties:
  test:
    type string
    default default value
```

**Avoid this pattern:**
```yaml
# NOT PREFERRED
allOf:
  - $ref /fragment/common/2.0.0#
  - properties:
      test:
        type string
        default default value
```

### Frequently Used Fields

#### HTTP Information

Include HTTP request/response metadata using fragment schemas:

```yaml
allOf:
  - $ref /fragment/common/2.0.0#
  - $ref /fragment/http/1.2.0#
```

**Client IP tracking** (if needed):
```yaml
allOf:
  - $ref /fragment/common/2.0.0#
  - $ref /fragment/http/1.2.0#
  - $ref /fragment/http/client_ip/1.0.0#
```

#### MediaWiki State Fragments

Use state entity fragments instead of common fragments:

**Available fragments:**
- `fragment/mediawiki/state/entity/page`
- `fragment/mediawiki/state/entity/user`
- `fragment/mediawiki/state/entity/revision`
- `fragment/mediawiki/state/entity/revision_slots`
- `fragment/mediawiki/state/entity/content`
- `fragment/mediawiki/state/entity/page_link`

**Change fragments:**
- `fragment/mediawiki/state/change` - Base for entity state changes

**Don't use**: `fragment/mediawiki/*/common` (deprecated)

##### JSON Integer Limitations and MediaWiki IDs

MediaWiki IDs changed from `UNSIGNED INT` to `UNSIGNED BIGINT`.

**Constraints enforced**:
```yaml
rev_id:
  description The database revision ID
  type integer
  maximum 9007199254740991  # MAX_SAFE_INTEGER
  minimum 1
```

**Values:**
- `UNSIGNED INT` max: 4,294,967,295
- `MAX_SAFE_INTEGER`: 9,007,199,254,740,991
- `UNSIGNED BIGINT` max: 18,446,744,073,709,551,615

**Current status**: Wikidata's highest revision (~2.2B) is halfway to `MAX_SAFE_INTEGER`. Future consideration: JavaScript BigInt (strings) instead.

#### Common Analytics Fields

Standardized fields in `schemas/event/secondary`:

See [Analytics Fragments](https://wikitech.wikimedia.org/wiki/Event_Platform/Analytics/Fragments).

Common fields include:
- `device_id`
- `session_id`
- `pageview_id`
- And many more for analytics use cases

### Automatically Populated Fields

EventGate auto-populates these fields if in schema but not in event:

| Field | Source | Description |
|--------|---------|-------------|
| `$schema` | `schema_uri` query param | Schema URI |
| `meta.stream` | `stream` query param | Stream name |
| `meta.dt` | Server timestamp | Current ISO-8601 UTC time |
| `meta.id` | Generated | New UUID |
| `http.client_ip` | `X-Client-IP` header | Client IP address |
| HTTP headers | `enrich_fields_with_http_headers` config | Per stream configuration |

**Note**: For HTTP-specific headers, configure `producers.eventgate.enrich_fields_with_http_headers` in stream config.

### Event Data Modeling and Schema Naming

**Core principle**: We are modeling EVENTS, not entities.

#### Naming Guidelines

Name schemas as **actions happening to something** (verb + object).

**Good examples:**
- `entity/create`, `entity/delete`, `entity/change`
- `button/clicked`, `button/hovered`, `popup/displayed`
- `interface/interaction`
- `funnel/state_change`
- `search/request`

**Bad examples:**
- `mobile_app` (What happened?)
- `user` (Too vague)
- `page` (Too vague)
- `recommendation` (What event?)

**Naming test**: Ask "What is a `<schema_name>` event?" Does it make sense?

**Alternative patterns**:
- Use same schema for multiple state changes to same entity
  - `popup/visibility_change` with `action: displayed` or `action: hidden`
- Both approaches acceptable; focus on clarity

## Best Practices Summary

### DO:
- ✅ Use snake_case for all identifiers
- ✅ Include all required fields (`$schema`, `meta`, `meta.stream`, `meta.dt`, `dt`)
- ✅ Add examples to schemas
- ✅ Use ISO-8601 with UTC for datetime fields (`_dt` suffix)
- ✅ Omit optional fields instead of setting to `null`
- ✅ Use simple array/map types for schema evolution
- ✅ Model state changes with current + previous state
- ✅ Name schemas as events (actions)
- ✅ Add new optional fields for backwards compatibility

### DON'T:
- ❌ Use union types or `null` values
- ❌ Use `additionalProperties: true` for non-map objects
- ❌ Change types of existing fields
- ❌ Remove or rename existing fields
- ❌ Delete schemas
- ❌ Use mixed case for field names
- ❌ Use special characters in identifiers
- ❌ Use complex types in arrays/maps if evolution needed
- ❌ Name schemas as entities or systems (e.g., "user", "mobile_app")

## References

- [Event Platform Documentation](https://wikitech.wikimedia.org/wiki/Event_Platform)
- [Event Platform/Schemas](https://wikitech.wikimedia.org/wiki/Event_Platform/Schemas)
- [Stream Configuration](https://wikitech.wikimedia.org/wiki/Event_Platform/Stream_Configuration)
- [Schema Registry](https://schema.wikimedia.org/)
- [Primary Schema Repository](https://gitlab.wikimedia.org/repos/data-engineering/schemas-event-primary)
- [Event Utilities Client Libraries](https://wikitech.wikimedia.org/wiki/Event_Platform/Event_Utilities)
