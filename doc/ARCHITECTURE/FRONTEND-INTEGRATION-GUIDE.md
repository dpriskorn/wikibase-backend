# Frontend Integration Guide

## Status Flags

This guide explains how to work with item status flags for decentralized WikiProject governance.

### Computing is_dangling

The `is_dangling` flag should be computed by frontend on every revision by checking for the P6104 (maintained by WikiProject) statement:

```javascript
function isDangling(entity) {
  // Check if entity has P6104 (maintained by WikiProject) statement
  const claims = entity.claims || {};
  return !claims.hasOwnProperty('P6104') || claims['P6104'].length === 0;
}
```

### Setting Status Flags

When creating or updating an entity, include status flags in the request:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {"en": {"language": "en", "value": "Douglas Adams"}},
  "claims": {...},
  "is_semi_protected": false,
  "is_locked": false,
  "is_archived": false,
  "is_dangling": true,
  "is_mass_edit_protected": false,
  "is_not_autoconfirmed_user": false,
  "edit_type": "manual-update"
}
```

### Status Flag Descriptions

| Flag | Description | Who Can Set | Blocks |
|-------|-------------|--------------|--------|
| `is_semi_protected` | Item is semi-protected (blocks new/unconfirmed users) | WikiProject admins | Edits from not-autoconfirmed users |
| `is_locked` | Item is locked from all edits | WikiProject admins | All edits |
| `is_archived` | Item is archived (cannot be edited, can be excluded from exports) | Wikidata community admins | All edits |
| `is_dangling` | Item has no maintaining WikiProject (P6104 statement) | Frontend (computed) | None |
| `is_mass_edit_protected` | Item is protected from mass edits (bot operations) | WikiProject admins | Mass edits only |

---

## Protection Workflow

### Semi-Protection (WikiProject Level)

Semi-protection blocks edits from new or unconfirmed users while allowing autoconfirmed users to make changes.

To semi-protect an item:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_semi_protected": true,
  "edit_type": "semi-protection-added"
}
```

To remove semi-protection:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_semi_protected": false,
  "edit_type": "semi-protection-removed"
}
```

**Request must include user context:**

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {"en": {"language": "en", "value": "Updated"}},
  "is_not_autoconfirmed_user": false
}
```

Frontend determines autoconfirmed status based on user account (e.g., account age > 10 days AND edit count > 10).

### Lock (WikiProject Level)

Locking prevents ALL edits, including manual edits from trusted users.

To lock an item:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_locked": true,
  "edit_type": "lock-added"
}
```

To unlock:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_locked": false,
  "edit_type": "lock-removed"
}
```

### Mass-Edit Protection (WikiProject Level)

Mass-edit protection blocks bot and batch operations while allowing manual edits.

To protect an item from mass edits:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_mass_edit_protected": true,
  "edit_type": "mass-protection-added"
}
```

To remove mass-edit protection:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_mass_edit_protected": false,
  "edit_type": "mass-protection-removed"
}
```

### Archive (Wikidata Level)

Archiving is for items that are stale or obsolete and no longer curated. Archived items can be excluded from exports and weekly RDF dumps.

To archive an item:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_archived": true,
  "edit_type": "archive-added"
}
```

To unarchive:

```json
{
  "id": "Q42",
  "type": "item",
  "labels": {...},
  "is_archived": false,
  "edit_type": "archive-removed"
}
```

---

## Querying Status Flags

### Query Locked Items

```
GET /entities?status=locked&limit=100
```

Returns list of entity IDs that are currently locked.

### Query Semi-Protected Items

```
GET /entities?status=semi_protected&limit=100
```

Returns list of entity IDs that are currently semi-protected.

### Query Archived Items

```
GET /entities?status=archived&limit=100
```

Returns list of entity IDs that are currently archived.

### Query Dangling Items

```
GET /entities?status=dangling&limit=100
```

Returns list of entity IDs that have no maintaining WikiProject. This is useful for WikiProjects to identify items that need adoption.

---

## EditType Values

Standard edit types for classification and filtering:

### Protection Management
- `lock-added` - Item was locked
- `lock-removed` - Item lock was removed
- `semi-protection-added` - Semi-protection was added
- `semi-protection-removed` - Semi-protection was removed
- `mass-protection-added` - Mass-edit protection was added
- `mass-protection-removed` - Mass-edit protection was removed
- `archive-added` - Item was archived
- `archive-removed` - Item was unarchived

### Mass Edit Classifications
- `bot-import` - Bot import operation
- `bot-cleanup` - Bot cleanup operation
- `bot-merge` - Bot merge operation
- `bot-split` - Bot split operation

### Manual Edit Classifications
- `manual-create` - Manual entity creation
- `manual-update` - Manual entity update
- `manual-correction` - Manual correction

### Cleanup Campaigns
- `cleanup-2025` - 2025 cleanup campaign
- `cleanup-labels` - Label cleanup
- `cleanup-descriptions` - Description cleanup

### Migration Operations
- `migration-initial` - Initial migration
- `migration-batch` - Batch migration

### Default
- `` (empty string) - Unspecified edit type

---

## EntityCreateRequest Fields

| Field | Type | Default | Description |
|--------|------|----------|-------------|
| `id` | string | required | Entity ID (e.g., Q42) |
| `type` | string | "item" | Entity type |
| `labels` | object | null | Entity labels |
| `descriptions` | object | null | Entity descriptions |
| `claims` | object | null | Entity claims |
| `aliases` | object | null | Entity aliases |
| `sitelinks` | object | null | Entity sitelinks |
| `is_mass_edit` | boolean | false | Whether this is a mass edit |
| `edit_type` | string | "" | Edit type classification |
| `is_semi_protected` | boolean | false | Item is semi-protected |
| `is_locked` | boolean | false | Item is locked |
| `is_archived` | boolean | false | Item is archived |
| `is_dangling` | boolean | false | Item has no maintaining WikiProject |
| `is_mass_edit_protected` | boolean | false | Item is protected from mass edits |
| `is_not_autoconfirmed_user` | boolean | false | User is not autoconfirmed (new/unconfirmed account) |

---

## Querying by Edit Type

You can query entities by their latest revision's edit type:

```
GET /entities?edit_type=lock-added&limit=100
GET /entities?edit_type=archive-removed&limit=100
GET /entities?edit_type=bot-import&limit=100
```

This is useful for:
- Finding all items that were recently locked
- Identifying items affected by a specific cleanup campaign
- Auditing protection changes

---

## Protection Enforcement

The backend enforces protection rules in the following priority order:

1. **Archived items** → Reject ALL edits with message: "Item is archived and cannot be edited"
2. **Locked items** → Reject ALL edits with message: "Item is locked from all edits"
3. **Mass-edit protected items** → Reject MASS edits only with message: "Mass edits blocked on this item"
4. **Semi-protected items** → Reject edits from NOT-AUTOCONFIRMED users with message: "Semi-protected items cannot be edited by new or unconfirmed users"

Protection is checked on the **current head revision** before allowing any edit.

### Protection Priority Example

An item with:
- `is_archived: true`
- `is_locked: false`
- `is_semi_protected: true`
- `is_mass_edit_protected: true`

Will block ALL edits because `is_archived` takes priority.

---

## Export Filtering

Archived items can be excluded from exports and dumps by filtering on the `is_archived` flag:

**In Vitess (entity_head table):**
```sql
SELECT m.external_id
FROM entity_head h
JOIN entity_id_mapping m ON h.entity_id = m.internal_id
WHERE h.is_archived = FALSE;
```

**In S3 (revision metadata):**
```json
{
  "is_archived": false,
  // ... other fields
}
```

Export services should check this flag to decide whether to include an entity in:
- Weekly RDF dumps
- Full export bundles
- Change event streams

---

## Audit Trail

Every protection change is tracked through:

1. **`edit_type`** - Indicates what protection action was taken (e.g., "lock-added")
2. **`created_by`** - User or system that made the change
3. **`created_at`** - When the change was made
4. **Revision history** - All protection changes are preserved in the immutable revision history

To view protection history for an item, use the revision history endpoint and filter by `edit_type` values containing "lock", "protection", or "archive".

---

## Best Practices

### For WikiProjects

1. **Adopt dangling items**: Use the dangling query to find items without maintainers
2. **Use semi-protection by default**: Protect from mass edits but allow trusted edits
3. **Use locking sparingly**: Only lock during disputes or vandalism spikes
4. **Document protection reasons**: Use `edit_type` consistently

### For Wikidata Community Admins

1. **Archive dormant items**: Use archive for items from inactive WikiProjects
2. **Keep archives reversible**: Archived items can be unarchived if WikiProject revives
3. **Monitor dangling ratio**: Keep dangling items under 1% (as per governance proposal)

### For Frontend Developers

1. **Always compute is_dangling**: On every entity update, check for P6104 statement
2. **Use appropriate edit_type**: Always include protection-related edit types
3. **Handle protection errors**: Display user-friendly messages for 403 errors
4. **Query status before editing**: Check `is_locked` or `is_archived` before allowing edit UI

---

## Example Workflows

### Workflow 1: WikiProject Adopts Dangling Items

1. Query dangling items: `GET /entities?status=dangling&limit=100`
2. User reviews and selects items to adopt
3. Frontend updates items with P6104 claim (adding WikiProject reference)
4. Frontend sets `is_dangling: false` and `edit_type: "manual-update"`
5. API accepts the update

### Workflow 2: WikiProject Semi-Protects Item After Vandalism

1. User detects vandalism on item Q42
2. User clicks "semi-protect" button
3. Frontend sends:
   ```json
   {
     "id": "Q42",
     "labels": {"en": {"language": "en", "value": "Corrected label"}},
     "is_semi_protected": true,
     "edit_type": "semi-protection-added"
   }
   ```
4. API accepts and stores protection
5. Future mass edits to Q42 are rejected

### Workflow 3: Wikidata Community Archives Items from Inactive WikiProject

1. WikiProject marked as dormant (no activity for 6 months)
2. Community admin decides to archive its items
3. Query items maintained by WikiProject: `GET /entities?edit_type=semi-protection-added&limit=1000`
4. Batch archive items:
   ```json
   {
     "id": "Q12345",
     "is_archived": true,
     "edit_type": "archive-added"
   }
   ```
5. Export services exclude archived items from future dumps
6. If WikiProject revives, items can be unarchived with `archive-removed`

---

## Error Handling

### HTTP 403 Errors

When an edit is rejected due to protection, the API returns:

```json
{
  "detail": "Item is locked from all edits"
}
```

Error messages:
- `"Item is archived and cannot be edited"` - Item is archived
- `"Item is locked from all edits"` - Item is locked
- `"Mass edits blocked on semi-protected item"` - Mass edit attempted on semi-protected item

Frontend should display these messages to the user and provide appropriate UI options (e.g., "Request unprotection" button).

---

## API Response Changes

### Create Entity Response

Status flags are now included in the response:

```json
{
  "id": "Q42",
  "revision_id": 5,
  "data": {
    "id": "Q42",
    "type": "item",
    "labels": {...}
  },
  "is_semi_protected": false,
  "is_locked": false,
  "is_archived": false,
  "is_dangling": true
}
```

### Get Entity Response

Same structure as create response - includes all status flags from the current head revision.
