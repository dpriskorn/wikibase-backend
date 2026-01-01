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

### hashing/value_node_hasher.py
**MediaWiki-compatible value node hash generation.**

**Class:** `ValueNodeHasher`
- **Purpose:** Generates value node URIs (wdv:) using MediaWiki's exact hash format
- **Methods:**
  - `_format_precision(value: float) -> str` - Normalizes precision to remove leading zero in exponent
  - `hash_globe_coordinate(latitude, longitude, precision, globe) -> str` - Hash globe coordinates
  - `hash_time_value(time_str, precision, timezone, calendar) -> str` - Hash time values (keeps leading + in hash)
  - `hash_quantity_value(value, unit, upper_bound, lower_bound) -> str` - Hash quantity values
  - `hash_entity_value(value) -> str` - Hash entity values

**Format Compatibility:**
- Precision normalization: `1.0E-05` → `1.0E-5` (removes leading zero after E)
- Globe coordinate format: `value/P625:lat:lon:precision:globe` (matches MediaWiki test expectations)
- Time value format: `t:+time:precision:timezone:calendar` (leading + preserved in hash)

**Recent Improvements:**
- ✓ Created MediaWiki-compatible hash generation
- ✓ Fixed precision normalization (line 15-26)
- ✓ Matched MediaWiki test hash values for globe coordinates
- ✓ Matched MediaWiki test hash values for time values

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
  - **FIXED:** Now correctly normalizes `Q123$ABC-DEF` → `Q123-ABC-DEF`
  - Only first `$` after entity ID boundary replaced with `-`
  - Follows MediaWiki's `preg_replace('/[^\w-]/', '-', $guid)` pattern
- `reference_uri(stmt_uri, idx)` - Reference node URI

**Recent Improvements:**
- ✓ Fixed statement ID normalization to match MediaWiki's approach
- ✓ Tests confirm correct URI generation for statement nodes

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

## Testing Strategy

### Test Pyramid

The testing approach follows a pyramid structure with three levels:

```
        Integration Tests (Phase 3)
              ↑↑↑
      Writer/Component Tests (Phase 2)
              ↑↑↑
         Unit Tests (Phase 1)
```

### Phase 1: Unit Tests (Lowest Level) ✅ COMPLETE

**Purpose:** Test individual components in isolation

**Test Files:**
- `test_value_node.py` - Value node URI generation and serialization (7 tests)
- `test_normalization.py` - RDF normalization utilities

**Coverage:**
- `ValueNode.generate_value_node_uri()` - MD5-based URI generation
- `ValueNode._serialize_value()` - Value serialization for hashing
- URI consistency for identical values
- URI differentiation for different properties

### Phase 2: Writer Tests (Mid Level) ✅ COMPLETE

**Purpose:** Test RDF writing components with small inputs

**Test Files:**
- `test_value_node_writer.py` - Structured value node writing (5 tests)
- `test_triple_writer_value_nodes.py` - Value node detection (4 tests)
- `test_property_ontology.py` - Property metadata and predicates (9 tests)
- `test_property.py` - Basic property writing
- `test_property_registry.py` - Property registry loading (8 tests)
- `test_referenced_entities.py` - Referenced entity collection (4 tests)

**Coverage:**
- `ValueNodeWriter.write_time_value_node()` - Time value nodes with all fields
- `ValueNodeWriter.write_quantity_value_node()` - Quantity nodes with bounds
- `ValueNodeWriter.write_globe_value_node()` - Globe coordinate nodes
- `TripleWriters.write_statement()` - Full statement writing
- `TripleWriters.write_direct_claim()` - Direct claim generation
- `PropertyOntologyWriter.write_property_metadata()` - Property metadata blocks
- `PropertyOntologyWriter.write_property()` - Predicate declarations
- `PropertyOntologyWriter.write_novalue_class()` - No-value constraints
- `PropertyRegistry.shape()` - Property shape lookup
- `EntityConverter._collect_referenced_entities()` - Referenced entity collection
- `EntityConverter._write_referenced_entity_metadata()` - Referenced entity metadata

### Phase 3: Integration Tests (Higher Level) 🔄 IN PROGRESS

**Purpose:** Test complete conversion of entities to RDF

**Test Files:**
- `test_q42_conversion.py` - Large entity integration test
- `test_q120248304_conversion.py` - Medium entity with globe coordinates
- `test_ttl_comparison.py` - TTL comparison utilities
- `test_split_blocks.py` - Turtle block splitting

**Coverage:**
- EntityConverter.convert_to_string() - Full entity conversion
- Statement URI generation (wds: prefix with UUID)
- Reference URI generation (wdref: prefix with hash)
- Direct claim generation for best-rank statements
- Value node generation for time, quantity, globe coordinates
- Qualifier and reference value nodes

**Current Status (Q120248304):**
```
Actual blocks: 167
Golden blocks: 167
Missing: 2 (correct hashes!)
Extra: 2 (deduplication issue)
```

**Test Results:**
- ✓ Statement ID normalization working correctly
- ✓ MediaWiki hash matching for globe coordinates
- ✓ MediaWiki hash matching for time values
- ❌ Value node deduplication not working (same values written twice with different hashes)

**Planned Test Suites:**

**Suite 3.1: Basic Entity Features**
- Labels (single and multiple languages)
- Descriptions (single and multiple languages)
- Aliases (multiple per language)
- Sitelinks
- Entity type declaration

**Suite 3.2: Statement Features**
- Entity value statements
- String value statements
- Time value statements
- Quantity value statements
- Globe coordinate statements
- Monolingualtext statements
- External-id statements
- Statement ranks (normal, preferred, deprecated)
- Statement qualifiers (with value nodes)
- Statement references (with value nodes)

**Suite 3.3: Property Metadata**
- Property entity metadata blocks
- Property predicate declarations (p, ps, pq, pr, wdt, psv, pqv, prv)
- No-value constraints with blank nodes
- Multi-language labels and descriptions

**Suite 3.4: Value Nodes**
- Time value nodes (all fields)
- Quantity value nodes (with bounds)
- Globe coordinate value nodes
- Qualifier value nodes
- Reference value nodes

### Phase 4: Roundtrip Tests 🔴 NEEDED

**Purpose:** Compare generated TTL with golden files from Wikidata

**Test Files:**
- **Planned:** `test_roundtrip_q17948861.py` - Small entity roundtrip
- **Planned:** `test_roundtrip_q42.py` - Large entity roundtrip
- **Planned:** `test_roundtrip_q120248304.py` - Medium entity roundtrip

**Coverage:**
- Parse entity JSON
- Generate TTL
- Split TTL into subject blocks
- Compare block-by-block with golden TTL
- Verify all RDF blocks present and correct

**Known Failure:**
- `test_q17948861_full_roundtrip` - Missing 10 of 13 RDF blocks
  - Missing: Referenced entity metadata, property predicate declarations, no-value constraints
  - Root cause: Implementation complete but not fully integrated
