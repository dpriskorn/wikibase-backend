# S3 Revision Schema v1.0.0

Initial schema definition for immutable entity revision snapshots.

## Changes from previous version

Initial release.

## Schema

See `schema.json` for complete definition.

## Example

```json
{
  "schema_version": "1.0.0",
  "entity_id": "Q42",
  "revision_id": 1,
  "created_at": "2025-01-15T10:30:00Z",
  "created_by": "user:ExampleUser",
  "entity_type": "item",
  "entity": {
    "id": "Q42",
    "type": "item",
    "labels": {"en": {"language": "en", "value": "Douglas Adams"}},
    "descriptions": {},
    "aliases": {},
    "claims": {},
    "sitelinks": {}
  }
}
```
