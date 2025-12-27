# Test Data Directory

This directory contains expected responses and data structures for integration testing.

## Directory Structure

```
test_data/
├── revisions/       # Expected raw entity data in full S3 revision schema format
│   ├── Q12345_r1.json
│   ├── Q12345_r2.json
│   └── Q42_r1.json
└── errors/         # Expected error responses
    ├── entity_not_found.json
    ├── no_revisions.json
    └── revision_not_found.json
```

## Revisions

Files in `revisions/` follow the S3 revision schema v1.0.0 format:

```json
{
  "schema_version": "1.0.0",
  "entity_id": "Q12345",
  "revision_id": 1,
  "created_at": "2025-12-27T14:48:50Z",
  "created_by": "integration_test",
  "entity_type": "item",
  "entity": {
    "id": "Q12345",
    "type": "item",
    "labels": {...}
  }
}
```

Note: The `/raw/{entity_id}/{revision_id}` endpoint currently returns only the inner `entity` object, not the full wrapper. This test data represents what **should** be stored per the schema, which will be used for future validation and migration testing.

## Errors

Files in `errors/` contain expected 404 error responses:

- `entity_not_found.json`: Entity ID not in ID mapping table
- `no_revisions.json`: Entity exists but has no revisions in database
- `revision_not_found.json`: Requested revision ID doesn't exist for entity

## Usage

Test files load this data to verify expected behavior:

```python
from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"

# Load expected revision data
with open(TEST_DATA_DIR / "revisions/Q12345_r1.json") as f:
    expected_revision = json.load(f)

# Load expected error
with open(TEST_DATA_DIR / "errors/entity_not_found.json") as f:
    expected_error = json.load(f)
```
