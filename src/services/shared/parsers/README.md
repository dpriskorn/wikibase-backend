# Parser Documentation

This directory contains parsers for converting Wikibase JSON to the Internal Representation (IR).

## Architecture

The parsing pipeline follows this flow:

```
Wikibase JSON → Value Parsers → IR Models → RDF Emitters → RDF
```

The **Value Parser Dispatcher** is the critical single choke point between JSON and IR.

## Value Parser Dispatcher

**File:** `value_parser.py`

**Purpose:** Centralized dispatcher that maps Wikibase datatypes to their specific parsers.

**Design Benefits:**
- ✅ **Strong typing** - dict lookup is type-safe with mypy
- ✅ **Early validation** - fail fast at dispatcher level, not deep in parsing
- ✅ **Order independence** - no linear if/elif chain, O(1) dict lookup
- ✅ **Deterministic hashing** - same input always produces same IR
- ✅ **Easy extensibility** - add new value type = one dict entry + one function
- ✅ **Clean RDF emission** - consistent, validated IR for emitters

## Parser Functions

### Entry Point

**`parse_value(snak_json: dict[str, Any]) -> Value`**

Main dispatcher function that:
1. Validates snak is `"value"` type (not novalue/somevalue)
2. Extracts `datatype` and `datavalue` from snak
3. Looks up parser in `PARSERS` dictionary
4. Delegates to specific parser function
5. Returns typed IR Value object

### Value-Specific Parsers

**Directory:** `values/`

All parser functions follow this signature:
```python
def parse_{type_name}_value(datavalue: dict[str, Any]) -> {Type}Value:
    # Extract fields using JsonField enums
    # Return IR Value object
```

**Parsers:**
- `parse_entity_value()` - Entity references (Q42, P31)
- `parse_string_value()` - String values
- `parse_time_value()` - Time values with precision/calendar
- `parse_quantity_value()` - Quantity values with bounds
- `parse_globe_value()` - Globe coordinates (lat/long/altitude)
- `parse_monolingual_value()` - Monolingual text (language + text)
- `parse_external_id_value()` - External identifiers
- `parse_commons_media_value()` - Commons media files
- `parse_geo_shape_value()` - Geographic shapes
- `parse_tabular_data_value()` - Tabular data
- `parse_musical_notation_value()` - LilyPond musical notation
- `parse_url_value()` - HTTP/HTTPS URLs
- `parse_math_value()` - LaTeX mathematical expressions
- `parse_entity_schema_value()` - Entity schema references

## JSON Field Enums

**File:** `src/services/shared/models/internal_representation/json_fields.py`

All JSON field names are defined as enums to avoid string literals:

```python
JsonField.TYPE.value  # "type"
JsonField.VALUE.value  # "value"
JsonField.PROPERTY.value  # "property"
# ... etc
```

## Usage Example

```python
from services.shared.parsers import parse_value

# Parse a snak from Wikibase JSON
snak_json = {
    "snaktype": "value",
    "property": "P31",
    "datatype": "wikibase-item",
    "datavalue": {
        "value": {"entity-type": "item", "numeric-id": 5, "id": "Q5"},
        "type": "wikibase-entityid"
    }
}

# Returns EntityValue instance
ir_value = parse_value(snak_json)
assert ir_value.kind == "entity"
assert ir_value.value == "Q5"
```

## Error Handling

- **ValueError**: Raised for:
  - Unsupported datatypes
  - Non-value snaktypes (novalue, somevalue)
  - Invalid data format (caught by Pydantic validators)

## Related Models

See `src/services/shared/models/internal_representation/` for IR model definitions:

- `vocab.py` - RDF vocabulary (WD, WDT, P, PS, PQ, PR, WDS, WDREF)
- `ranks.py` - Rank enum (preferred, normal, deprecated)
- `entity_types.py` - EntityKind enum (item, property)
- `values/` - Value type models
- `qualifiers.py` - Qualifier model
- `references.py` - Reference and ReferenceValue models
- `statements.py` - Statement model
- `entity.py` - Entity model
