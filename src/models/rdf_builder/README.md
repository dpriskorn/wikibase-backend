# RDF Builder

## Overview

Converts internal Entity models to RDF (Turtle format) following Wikibase RDF mapping rules.

**Parser Status:** ✓ COMPLETE
**RDF Generation Status:** 🟡 IN PROGRESS - Value nodes remaining

### Parser Capabilities

- ✓ Entity parsing (Entity model)
- ✓ Labels (72 languages in Q42)
- ✓ Descriptions (116 languages in Q42)
- ✓ Aliases (25 entries in Q42)
- ✓ Statements (332 statements across 293 properties)
- ✓ Qualifiers (nested in statements)
- ✓ References (nested in statements)
- ✓ Sitelinks (129 entries in Q42)
- ✓ All value types (entity, time, string, quantity, etc.)
- ✓ All ranks (normal, preferred, deprecated)
- ✓ All snaktypes (value, novalue, somevalue)

### RDF Generation Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Entity type declaration | ✓ Implemented | `wikibase:Item` |
| Labels | ✓ Implemented | `rdfs:label` triples |
| Descriptions | ✓ Implemented | `schema:description` triples |
| Aliases | ✓ Implemented | `skos:altLabel` triples |
| Statements (basic) | ✓ Implemented | `p:Pxxx`, `ps:Pxxx` triples |
| Statement rank types | ✓ Implemented | BestRank, NormalRank, DeprecatedRank |
| Qualifiers | ✓ Implemented | `pq:Pxxx` triples with values |
| References | ✓ Implemented | `pr:Pxxx` triples with values |
| Sitelinks | ✓ Implemented | `schema:sameAs` triples |
| Dataset metadata | ✓ Implemented | Software version, dateModified, counts |
| Turtle prefixes | ✓ Implemented | 30 prefixes for output |
| **Structural Support** | | |
| Property metadata structure | ✓ Implemented | PropertyShape has labels/descriptions fields |
| Property metadata loading | ✓ Implemented | Loader merges JSON + CSV, with tests |
| **Property Metadata Output** | | |
| Property metadata integration | ✓ Implemented | `EntityConverter._write_property_metadata()` writes all property blocks |
| Property metadata RDF output | ✓ Implemented | `write_property_metadata()` generates wd:Pxxx blocks |
| Property entity metadata | ✓ Implemented | Property metadata block with labels, descriptions |
| Property predicate declarations | ✓ Implemented | `write_property()` generates owl:ObjectProperty |
| Property value predicates | ✓ Implemented | `write_property_metadata()` includes value predicates |
| No value constraints | ✓ Implemented | `write_novalue_class()` generates wdno:Pxxx blocks |
| Direct claim triples | ✓ Implemented | `write_direct_claim()` generates wdt:Pxxx for best-rank |
 | Referenced entity metadata | ✓ Implemented | Collects and writes wd:Qxxx metadata blocks |
 | **Structured Value Nodes** | | |
 | Time value decomposition | ✓ Implemented | `wdv:` nodes with timeValue, timePrecision, timeTimezone, timeCalendarModel |
 | Quantity value decomposition | ✓ Implemented | `wdv:` nodes with quantityAmount, quantityUnit |
 | Globe coordinate decomposition | ✓ Implemented | `wdv:` nodes with geoLatitude, geoLongitude, geoPrecision, geoGlobe |
 | Value node linking | ✓ Implemented | psv:Pxxx predicates link statements to wdv: nodes |
 | Value node URI generation | ✓ Implemented | MD5-based hash for consistent `wdv:` IDs |

---

## Architecture Overview

Based on `doc/ARCHITECTURE/JSON-RDF-CONVERTER.md`:

```
Entity (internal model)
     ↓
EntityConverter.convert_to_turtle()
     ↓
TripleWriters methods
     ↓
Turtle format RDF
```
Entity JSON (Wikidata API)
          ↓
    parse_entity() → Entity model
          ↓
    EntityConverter(property_registry=registry)
          ↓
    convert_to_turtle(entity, output)
          ↓
    TripleWriters methods:
   - write_entity_type()
   - write_dataset_triples()
   - write_label() (per language)
   - write_statement() (per statement)
     → ValueFormatter.format_value()
          ↓
    Turtle format RDF
```

---

## Components

### converter.py
**Main conversion class** that orchestrates RDF generation.

**Class:** `EntityConverter`
- **Required fields:** `property_registry: PropertyRegistry`
- **Optional fields:** `entity_cache_path: Path` - Path to entity JSON files for referenced entities
- **Methods:**
  - `convert_to_turtle(entity, output: TextIO)` - Write RDF to output stream
  - `convert_to_string(entity) -> str` - Return RDF as string
  - `_write_property_metadata(entity, output)` - Write property metadata blocks for properties used in entity
  - `_collect_referenced_entities(entity)` - Collect unique entity IDs referenced in statement values
  - `_load_referenced_entity(entity_id)` - Load entity from JSON cache
  - `_write_referenced_entity_metadata(entity, output)` - Write metadata blocks for referenced entities

**Usage:**
```python
registry = PropertyRegistry(properties={...})
converter = EntityConverter(property_registry=registry)
ttl = converter.convert_to_string(entity)
```

### writers/triple.py
**Triple writing utilities** for RDF generation.

**Class:** `TripleWriters` (static methods)
- `write_entity_type(output, entity_id)` - Write `a wikibase:Item`
- `write_dataset_triples(output, entity_id)` - Write dataset metadata
- `write_label(output, entity_id, lang, label)` - Write `rdfs:label`
- `write_statement(output, entity_id, statement, shape)` - Write full statement block
- `write_direct_claim(output, entity_id, property_id, value)` - Write direct claim triple (wdt:Pxxx) for best-rank

**Class:** `PropertyOntologyWriter` (static methods)
- `write_property_metadata(output, shape)` - Write full property metadata block with labels, descriptions, predicate links
- `write_property(output, shape)` - Write property predicate declarations (`owl:ObjectProperty`)
- `write_novalue_class(output, property_id)` - Write no-value constraint block with blank node

### property_registry/
**Property metadata** for RDF predicate mappings.

- **registry.py** - `PropertyRegistry` lookup table
- **loader.py** - Load from JSON files (merges labels/descriptions from JSON with datatype from CSV)
- **models.py** - `PropertyShape`, `PropertyPredicates` data models

### ontology/
**Property shape factory** based on datatypes.

- **datatypes.py** - `property_shape(pid, datatype, labels, descriptions)` creates predicate configurations with metadata

### writers/prefixes.py
**Turtle prefix declarations** for RDF output.

**Constant:** `TURTLE_PREFIXES` - 21 standard Wikidata prefixes

### value_formatters.py
**Value formatting** for RDF literals/URIs.

**Class:** `ValueFormatter` (static methods)
- `format_value(value) -> str` - Format any Value object as RDF
- `escape_turtle(value) -> str` - Escape special characters

### uri_generator.py
**URI generation** for entities, statements, references.

**Class:** `URIGenerator`
- `entity_uri(entity_id)` - `http://www.wikidata.org/entity/Q42`
- `data_uri(entity_id)` - Dataset URI with `.ttl` suffix
- `statement_uri(statement_id)` - Statement node URI
- `reference_uri(stmt_uri, idx)` - Reference node URI

---

## Data Flow

```
Entity JSON (Wikidata API)
         ↓
parse_entity() → Entity model
         ↓
EntityToRdfConverter(properties=registry)
         ↓
convert_to_turtle(entity, output)
         ↓
TripleWriters methods:
  - write_entity_type()
  - write_dataset_triples()
  - write_label() (per language)
  - write_statement() (per statement)
    → ValueFormatter.format_value()
         ↓
Turtle format RDF
```

---

## Test Failures Analysis

### test_q17948861_full_roundtrip

**Status:** FAILING - Missing RDF blocks in generated output

**Error:**
```
assert actual_blocks.keys() == golden_blocks.keys()
```

**Actual blocks (3):**
- wd:Q17948861
- data:Q17948861
- wds:Q17948861-FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6

**Golden blocks (13):**
- data:Q17948861
- wd:Q17948861
- wds:Q17948861-FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6
- **wd:Q17633526** (referenced entity - "Wikinews article")
- **wd:P31** (property entity with metadata)
- **p:P31** (predicate declaration)
- **psv:P31** (statement value predicate)
- **pqv:P31** (qualifier value predicate)
- **prv:P31** (reference value predicate)
- **wdt:P31** (direct claim predicate)
- **ps:P31** (statement predicate)
- **pq:P31** (qualifier predicate)
- **pr:P31** (reference predicate)
- **wdno:P31** (no value property)
- **_:0b8bd71b926a65ca3fa72e5d9103e4d6** (blank node constraint)

**Root cause:** Converter only generates entity and statement blocks, missing:
1. Referenced entity metadata blocks
2. Property entity metadata blocks
3. Property predicate declarations (owl:ObjectProperty)
4. Property value predicate declarations
5. No value constraint blocks with blank nodes

**Impact:** Tests fail because Wikidata's RDF dumps include full property ontology and referenced entity descriptions.

**Design decision needed:** Should converter generate:
- Full property ontology (all properties used)?
- Only properties referenced in the entity?
- Option to include/exclude property metadata blocks?

---

## Usage Example

### Basic Entity Conversion

```python
from models.rdf_builder.converter import EntityConverter
from models.rdf_builder.property_registry.loader import load_property_registry
from models.json_parser.entity_parser import parse_entity

# Load property registry
registry = load_property_registry(Path("properties/"))

# Create converter
converter = EntityConverter(property_registry=registry)

# Parse entity JSON
with open("Q42.json", "r") as f:
    entity_json = json.load(f)
    entity = parse_entity(entity_json)

# Convert to Turtle
ttl = converter.convert_to_string(entity)
print(ttl)
```

### Output to File

```python
from io import StringIO

converter = EntityConverter(property_registry=registry)

# Write directly to file
with open("Q42.ttl", "w") as f:
    converter.convert_to_turtle(entity, f)
```

### Minimal Property Registry (for tests)

```python
from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.ontology.datatypes import property_shape

# Create minimal registry for specific entity
properties = {
    "P31": property_shape("P31", "wikibase-item"),
    "P17": property_shape("P17", "wikibase-item"),
    # ... add more properties as needed
}
registry = PropertyRegistry(properties=properties)

converter = EntityConverter(property_registry=registry)
```

---

## Implementation Status

**Recent Changes (Property Metadata Support):**

### Structural Changes (COMPLETED):
- ✓ PropertyShape model - Added `labels` and `descriptions` fields
- ✓ Loader - Merges labels/descriptions from JSON with datatype from CSV
- ✓ property_shape factory - Accepts optional labels/descriptions parameters
- ✓ Tests - Added comprehensive tests in `tests/rdf/test_property_registry.py`

**Property Ontology Writer Tests (tests/rdf/test_property_ontology.py):**
- ✓ `write_property_metadata()` - Generates full property metadata blocks
- ✓ `write_property()` - Generates predicate declarations
- ✓ `write_novalue_class()` - Generates no-value constraints
- ✓ Multi-language support for labels/descriptions
- ✓ Correct handling of time datatypes with value nodes

**Direct Claims Implementation (COMPLETED):**
- ✓ `write_direct_claim()` method - Generates `wdt:Pxxx` triples
- ✓ Integration with `write_statement()` - Only generates for best-rank (truthy) statements
- ✓ Tests - Added `tests/rdf/test_direct_claims.py` with 4 test cases

### Test Coverage:
- `test_property_shape_with_labels_and_descriptions()` - Verify PropertyShape stores labels/descriptions
- `test_property_shape_empty_labels_descriptions()` - Verify default empty dicts
- `test_property_shape_factory_with_labels_descriptions()` - Factory accepts metadata
- `test_property_shape_factory_without_labels_descriptions()` - Factory works without metadata
- `test_property_shape_factory_time_datatype_with_metadata()` - Time datatype with value_node
- `test_property_registry_shape_method()` - Registry returns PropertyShape with metadata
- `test_property_registry_shape_not_found()` - Registry raises KeyError for missing properties
- `test_loader_with_json_and_csv()` - Integration test: JSON + CSV merge
- `test_loader_without_csv_fallback_to_string()` - Fallback to "string" when no CSV
- `test_loader_empty_labels_descriptions()` - Handles missing labels/descriptions in JSON

**Direct Claims Tests (tests/rdf/test_direct_claims.py):**
- ✓ `write_direct_claim_basic()` - Basic direct claim triple generation
- ✓ `write_direct_claim_entity_value()` - Direct claim with entity value
- ✓ `test_entity_converter_generates_direct_claims_for_best_rank()` - Generates wdt:Pxxx for best-rank
- ✓ `test_entity_converter_no_direct_claim_for_non_best_rank()` - No wdt:Pxxx for deprecated statements

**Referenced Entity Tests (tests/rdf/test_referenced_entities.py):**
- ✓ `test_collect_referenced_entities()` - Collects unique entity IDs from statement values
- ✓ `test_write_referenced_entity_metadata()` - Writes wd:Qxxx metadata blocks
- ✓ `test_load_referenced_entity_missing_file()` - Raises FileNotFoundError for missing JSON
- ✓ `test_converter_with_cache_path_generates_referenced_entity()` - Integration test with full conversion

Looking at `test_data/rdf/ttl/Q17948861.ttl` vs generated output, following features are still missing:

### Missing Entity Features

**All entity features implemented:**
- ✓ Labels: `rdfs:label` triples
- ✓ Descriptions: `schema:description` triples
- ✓ Aliases: `skos:altLabel` triples
- ✓ Sitelinks: `schema:sameAs` triples

### Missing Statement Features

- **Referenced entity metadata**: Entities used as values need their own metadata blocks
  ```turtle
  # When P31 points to Q17633526, we need:
  wd:Q17633526 a wikibase:Item ;
    rdfs:label "Wikinews article"@en ;
    skos:prefLabel "Wikinews article"@en ;
    schema:name "Wikinews article"@en ;
    schema:description "used with property P31"@en .
  ```

- **Property entity metadata**: Properties need description blocks
  ```turtle
  wd:P31 a wikibase:Property ;
    rdfs:label "instance of"@en ;
    skos:prefLabel "instance of"@en ;
    schema:name "instance of"@en ;
    schema:description "type to which this subject corresponds..."@en ;
    wikibase:propertyType <http://wikiba.se/ontology#WikibaseItem> ;
    wikibase:directClaim wdt:P31 ;
    wikibase:claim p:P31 ;
    wikibase:statementProperty ps:P31 ;
    wikibase:statementValue psv:P31 ;
    wikibase:qualifier pq:P31 ;
    wikibase:qualifierValue pqv:P31 ;
    wikibase:reference pr:P31 ;
    wikibase:referenceValue prv:P31 ;
    wikibase:novalue wdno:P31 .
  ```

- **Property predicate declarations**: Each property needs owl:ObjectProperty declarations
  ```turtle
  p:P31 a owl:ObjectProperty .
  psv:P31 a owl:ObjectProperty .
  pqv:P31 a owl:ObjectProperty .
  prv:P31 a owl:ObjectProperty .
  wdt:P31 a owl:ObjectProperty .
  ps:P31 a owl:ObjectProperty .
  pq:P31 a owl:ObjectProperty .
  pr:P31 a owl:ObjectProperty .
  ```

- **No value constraints**: Blank node for novalue constraints
  ```turtle
  wdno:P31 a owl:Class ;
    owl:complementOf _:0b8bd71b926a65ca3fa72e5d9103e4d6 .

  _:0b8bd71b926a65ca3fa72e5d9103e4d6 a owl:Restriction ;
    owl:onProperty wdt:P31 ;
    owl:someValuesFrom owl:Thing .
  ```

- **Direct claim triples** (optional, for truthy values):
  ```turtle
  <entity_uri> wdt:P31 wd:Q17633526 .
  ```

### Missing Value Node Features

- **Structured value nodes**: Decompose complex datatypes into separate value nodes
  ```turtle
  <stmt_uri> psv:P625 wdv:9f0355cb43b5be5caf0570c31d4fb707 .

  wdv:9f0355cb43b5be5caf0570c31d4fb707 a wikibase:GlobecoordinateValue ;
    wikibase:geoLatitude "50.94636"^^xsd:double ;
    wikibase:geoLongitude "1.88108"^^xsd:double ;
    wikibase:geoPrecision "1.0E-5"^^xsd:double ;
    wikibase:geoGlobe <http://www.wikidata.org/entity/Q2> .
  ```

### Missing Dataset Features

**All dataset features implemented:**
- ✓ Software version: `schema:softwareVersion "1.0.0"`
- ✓ Entity version: `schema:version "2146196239"^^xsd:integer`
- ✓ Modification date: `schema:dateModified "2024-05-06T01:49:59Z"^^xsd:dateTime`
- ✓ Entity counts: `wikibase:statements`, `wikibase:sitelinks`, `wikibase:identifiers`
- ✓ License: `cc:license`
- ✓ Dataset type: `a schema:Dataset`

### Missing Output Features

**All output features implemented:**
- ✓ Turtle prefixes: 30 `@prefix` declarations

---

## Next Steps

### COMPLETED
- ✓ Collect referenced entities - Scan all statement values for entity references (wd:Qxxx) and collect unique set
- ✓ Generate referenced entity metadata - For each referenced entity, write full metadata block (labels, descriptions, aliases)
- ✓ Property metadata generation - For each property used in entity:
    - Write `wd:Pxxx a wikibase:Property` with labels, descriptions, propertyType
    - Write all 10 predicate declarations (directClaim, claim, statementProperty, etc.)
- ✓ Property predicate declarations - Generate `owl:ObjectProperty` blocks for each property predicate
- ✓ No value constraint blocks - Generate `wdno:Pxxx` with blank node `owl:complementOf`
- ✓ Direct claim triples - Generate `wdt:Pxxx` triples for best-rank (truthy) values
- ✓ Value node decomposition - Generate `wdv:` nodes for time, quantity, and globe coordinates
 - ✓ Value node linking - Use `psv:Pxxx` predicates to link statements to value nodes

### COMPLETED: Structured Value Node Implementation

**Value node ID generation** - ✓ Completed
- ✓ MD5-based hash for consistent `wdv:` IDs
- ✓ Tests passing for URI generation

**Time value decomposition** - ✓ Completed
- ✓ `wdv:` nodes with timeValue, timePrecision, timeTimezone, timeCalendarModel
- ✓ `write_time_value_node()` writer implemented

**Quantity value decomposition** - ✓ Completed
- ✓ `wdv:` nodes with quantityAmount, quantityUnit
- ✓ `write_quantity_value_node()` writer implemented

**Globe coordinate decomposition** - ✓ Completed
- ✓ `wdv:` nodes with geoLatitude, geoLongitude, geoPrecision, geoGlobe
- ✓ `write_globe_value_node()` writer implemented

**Value node linking** - ✓ Completed
- ✓ `psv:Pxxx` predicates link statements to `wdv:` nodes
- ✓ `_needs_value_node()` helper detects structured values
- ✓ Integrated into `write_statement()` method

**Test Results:**
- ✓ 58 tests passed, 2 skipped
- ✓ Value node writers tested (time, quantity, globe)
- ✓ Triple writer value node detection tested
- ✓ End-to-end conversion tested (Q120248304 with globe coordinates)

### Value Node Examples

Time value node:
```turtle
wds:Q182397-FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6 psv:P569 wdv:cd6dd2e48a93286891b0753a1110ac0a .

wdv:cd6dd2e48a93286891b0753a1110ac0a a wikibase:TimeValue ;
	wikibase:timeValue "1964-05-15T00:00:00Z"^^xsd:dateTime ;
	wikibase:timePrecision "11"^^xsd:integer ;
	wikibase:timeTimezone "0"^^xsd:integer ;
	wikibase:timeCalendarModel <http://www.wikidata.org/entity/Q1985727> .
```

Quantity value node:
```turtle
wds:Q182397-F7204F5E-AC17-4484-B35F-F3582715B77B psv:P1971 wdv:26735f5641071ce58303f506fe005a54 .

wdv:26735f5641071ce58303f506fe005a54 a wikibase:QuantityValue ;
	wikibase:quantityAmount "+3"^^xsd:decimal ;
	wikibase:quantityUnit <http://www.wikidata.org/entity/Q199> .
```


