# S3 Revision Schema

Immutable entity revision snapshots stored in S3.

## Versioning

Follows semantic versioning: `MAJOR.MINOR.PATCH`

- MAJOR: Breaking changes
- MINOR: Backward-compatible additions
- PATCH: Backward-compatible bug fixes

## Schema Files

- `1.0.0/schema.json` - Initial schema definition

## Storage

S3 object path: `s3://wikibase-revisions/{entity_id}/r{revision_id}.json`
