# RDF Builder

## Overview

Converts internal Entity models to RDF (Turtle format) following Wikibase RDF mapping rules.

**Parser Status:** ✓ COMPLETE  
**RDF Generation Status:** ⚠️ IN PROGRESS

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
| Descriptions | ✗ Not Started | `schema:description` triples |
| Aliases | ✗ Not Started | `skos:altLabel` triples |
| Statements (basic) | ✓ Implemented | `p:Pxxx`, `ps:Pxxx` triples |
| BestRank | ✗ Not Started | Missing from statement types |
| Direct claims | ✗ Not Started | `wdt:Pxxx` triples for truthy values |
| Qualifiers | ⚠️ Partial | Values written, but not verified |
| References | ⚠️ Partial | Link written, values need verification |
| Value nodes | ✗ Not Started | `wdv:` URIs for time/globe-coordinate |
| Sitelinks | ✗ Not Started | `schema:sameAs` triples |
| Dataset metadata | ⚠️ Partial | Missing version, dateModified, counts |
| Turtle prefixes | ✗ Not Started | Missing from output |

---

## Architecture Overview

Based on `doc/ARCHITECTURE/JSON-RDF-CONVERTER.md`:

```
Entity (internal model)
    ↓
EntityToRdfConverter.convert_to_turtle()
    ↓
TripleWriters methods
    ↓
Turtle format RDF
```

---

## Components

### converter.py
**Main conversion class** that orchestrates RDF generation.

**Class:** `EntityToRdfConverter`
- **Required fields:** `properties: PropertyRegistry`
- **Methods:**
  - `convert_to_turtle(entity, output: TextIO)` - Write RDF to output stream
  - `convert_to_string(entity) -> str` - Return RDF as string

**Usage:**
```python
registry = PropertyRegistry(properties={...})
converter = EntityToRdfConverter(properties=registry)
ttl = converter.convert_to_string(entity)
```

### writers/triple.py
**Triple writing utilities** for RDF generation.

**Class:** `TripleWriters` (static methods)
- `write_entity_type(output, entity_id)` - Write `a wikibase:Item`
- `write_dataset_triples(output, entity_id)` - Write dataset metadata
- `write_label(output, entity_id, lang, label)` - Write `rdfs:label`
- `write_statement(output, entity_id, statement, shape)` - Write full statement block

### property_registry/
**Property metadata** for RDF predicate mappings.

- **registry.py** - `PropertyRegistry` lookup table
- **loader.py** - Load from JSON files
- **models.py** - `PropertyShape`, `PropertyPredicates` data models

### ontology/
**Property shape factory** based on datatypes.

- **datatypes.py** - `property_shape(pid, datatype)` creates predicate configurations
- **wikibase.py** - Predicate URI generator

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

## Usage Example

### Basic Entity Conversion

```python
from models.rdf_builder.converter import EntityToRdfConverter
from models.rdf_builder.property_registry.loader import load_property_registry
from models.json_parser.entity_parser import parse_entity

# Load property registry
registry = load_property_registry(Path("properties/"))

# Create converter
converter = EntityToRdfConverter(properties=registry)

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

converter = EntityToRdfConverter(properties=registry)

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

converter = EntityToRdfConverter(properties=registry)
```

---

## Architecture Overview

Based on `doc/ARCHITECTURE/JSON-RDF-CONVERTER.md`:

Entity (internal model)
↓
RDF Generator
↓
Triples (Turtle format)


---

## Implementation Status

Looking at `test_data/rdf/ttl/Q120248304.ttl`, the following features are still missing:

### Missing Entity Features

- **Descriptions**: `schema:description` triples (one per language)
  ```turtle
  <entity_uri> schema:description "A test entity"@en .
  ```

- **Aliases**: `skos:altLabel` triples (one per alias)
  ```turtle
  <entity_uri> skos:altLabel "An alias"@en .
  ```

- **Sitelinks**: `schema:sameAs` triples (one per sitelink)
  ```turtle
  <entity_uri> schema:sameAs <https://en.wikipedia.org/wiki/Q42> .
  ```

### Missing Statement Features

- **BestRank**: Additional type for normal-rank statements
  ```turtle
  <stmt_uri> a wikibase:Statement, wikibase:BestRank ;
  ```

- **Direct claims**: `wdt:Pxxx` triples for truthy values
  ```turtle
  <entity_uri> wdt:P17 wd:Q142 .
  <entity_uri> wdt:P31 wd:Q1076486 .
  ```

- **Value nodes**: Structured data for complex datatypes
  ```turtle
  <stmt_uri> psv:P625 wdv:9f0355cb43b5be5caf0570c31d4fb707 .
  
  wdv:9f0355cb43b5be5caf0570c31d4fb707 a wikibase:GlobecoordinateValue ;
    wikibase:geoLatitude "50.94636"^^xsd:double ;
    wikibase:geoLongitude "1.88108"^^xsd:double ;
    wikibase:geoPrecision "1.0E-5"^^xsd:double ;
    wikibase:geoGlobe <http://www.wikidata.org/entity/Q2> .
  ```

### Missing Dataset Features

- **Complete metadata**: Software version, entity version, modification date, counts
  ```turtle
  <data_uri> schema:softwareVersion "1.0.0" ;
    schema:version "1954232723"^^xsd:integer ;
    schema:dateModified "2023-08-15T09:34:22Z"^^xsd:dateTime ;
    wikibase:statements "9"^^xsd:integer ;
    wikibase:sitelinks "0"^^xsd:integer ;
    wikibase:identifiers "1"^^xsd:integer .
  ```

### Missing Output Features

- **Turtle prefixes**: `@prefix` declarations at start of file
- **Property ontology**: RDF describing property predicates (deferred)

---

## Next Steps

1. Add Turtle prefix output to `convert_to_turtle()`
2. Implement descriptions, aliases, sitelinks writers
3. Add BestRank to statements
4. Generate direct claim triples
5. Create value node writer for time and globe-coordinate
6. Complete dataset metadata with version and counts

