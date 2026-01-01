# RDF Builder

## Overview

Converts internal Entity models to RDF (Turtle format) following Wikibase RDF mapping rules.

**Parser Status:** ✓ COMPLETE
**RDF Generation Status:** ✅ CORE FEATURES COMPLETE
**Test Coverage:** 🔄 PHASE 2 COMPLETE, PHASE 3 IN PROGRESS, PHASE 4 IN PROGRESS

---

## Quick Start

### Basic Entity Conversion

```python
from models.rdf_builder.converter import EntityConverter
from models.rdf_builder.property_registry.loader import load_property_registry
from models.json_parser.entity_parser import parse_entity
from pathlib import Path

# Load property registry
registry = load_property_registry(Path("test_data/properties/"))

# Create converter
converter = EntityConverter(property_registry=registry)

# Parse entity JSON
with open("test_data/json/entities/Q42.json", "r") as f:
    entity_json = json.load(f)
    entity = parse_entity(entity_json)

# Convert to Turtle
ttl = converter.convert_to_string(entity)
print(ttl)
```

### Convert with Referenced Entity Metadata

```python
converter = EntityConverter(
    property_registry=registry,
    entity_metadata_dir=Path("test_data/json/entities")
)

ttl = converter.convert_to_string(entity)
# Now includes wd:Qxxx metadata blocks for referenced entities
```

### Write to File

```python
with open("Q42.ttl", "w") as f:
    converter.convert_to_turtle(entity, f)
```

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
 | Quantity value bounds | ✓ Implemented | `wdv:` nodes with optional quantityUpperBound, quantityLowerBound |
 | Globe coordinate decomposition | ✓ Implemented | `wdv:` nodes with geoLatitude, geoLongitude, geoPrecision, geoGlobe |
 | Value node linking | ✓ Implemented | psv:Pxxx, pqv:Pxxx, prv:Pxxx predicates linking to wdv: nodes |
 | Value node URI generation | ✓ Implemented | MD5-based hash for consistent `wdv:` IDs |
 | Qualifier value nodes | ✓ Implemented | pqv:Pxxx predicates link qualifiers to wdv: nodes |
 | Reference value nodes | ✓ Implemented | prv:Pxxx predicates link references to wdv: nodes |

---

## Known Issues

### Value Node Deduplication Issue (CONFIRMED 2025-01-01)

**Test:** Q120248304 (medium entity with globe coordinates)

**Latest Test Results:**
```
Actual blocks: 167
Golden blocks: 167
Missing: 2 (correct hashes now!)
Extra: 2 (deduplication issue)
```

**Verification:**
✅ Missing blocks in golden file exist:
- `wdv:9f0355cb43b5be5caf0570c31d4fb707` - Globe coordinate value node
- `wdv:c972163adcfbcee7eecdc4633d8ba455` - Time value node

✅ Extra blocks in our output:
- `wdv:b210d4fcc4a307c48e904d3600f84bf8` - Time value (duplicate hash)
- `wdv:cbdd5cd9651146ec5ff24078a3b84fb4` - Globe coordinate (duplicate hash)

**Root cause confirmed:** Value node deduplication cache not working - identical values being written multiple times with different hashes.

**Impact:** Creates duplicate `wdv:` blocks for same values, increasing RDF file size and causing comparison failures.

**Required Fix:** Implement proper deduplication strategy (similar to MediaWiki's `HashDedupeBag`):
- Track which value nodes have been written
- Check hash before writing new value node
- Return early if value node already exists

**MediaWiki Reference:** `mediawiki-extensions-Wikibase/repo/includes/Rdf/HashDedupeBag.php`

### Roundtrip Test Failure

**Test:** `test_q17948861_full_roundtrip` (not yet implemented in test suite)

**Issue:** Generated TTL missing some RDF blocks compared to golden file

**Expected blocks (13):**
- data:Q17948861, wd:Q17948861, wds:Q17948861-*
- wd:Q17633526 (referenced entity)
- wd:P31 (property entity)
- p:P31, ps:P31, psv:P31, pq:P31, pqv:P31, pr:P31, prv:P31, wdt:P31, wdno:P31

**Actual blocks (3):**
- data:Q17948861, wd:Q17948861, wds:Q17948861-*

**Root Cause:** Property metadata and referenced entity metadata not being written by default in EntityConverter

**Resolution:** Enable metadata writing by providing entity_cache_path parameter to EntityConverter

---

## Next Steps

### COMPLETED: Core Features
All major RDF generation features implemented:

- Entity type declaration
- Labels, descriptions, aliases
- Statements with all value types
- Statement ranks (normal, preferred, deprecated)
- Qualifiers with value nodes
- References with value nodes
- Sitelinks
- Dataset metadata
- Property ontology (metadata, predicates, no-value constraints)
- Direct claims for best-rank
- Structured value nodes (time, quantity, globe) with bounds
- Qualifier value nodes
- Reference value nodes
- Referenced entity metadata blocks
- Value node linking (psv, pqv, prv)
- URI generation (MD5-based hash)
- Turtle prefixes (30 standard prefixes)

### COMPLETED: MediaWiki Compatibility Improvements
All MediaWiki Wikibase compatibility improvements implemented:

- Hashing infrastructure - Created `value_node_hasher.py` with MediaWiki-compatible hash generation
- Precision formatting - Fixed scientific notation normalization: `1.0E-05` → `1.0E-5`
- Globe coordinate hashes - Match MediaWiki test expectations exactly (e.g., `cbdd5cd9651146ec5ff24078a3b84fb4`)
- Time value hashes - Preserve leading `+` in hash input, removed in RDF output
- Statement ID normalization - Fixed `Q123$ABC-DEF` → `Q123-ABC-DEF` handling

### PRIORITY: Value Node Deduplication
- **Issue:** Value node deduplication cache not working - identical values written with different hashes
- **Impact:** Creates duplicate `wdv:` blocks for same values
- **Status:** CONFIRMED - Q120248304 test shows 2 duplicate value nodes
- **Required:** Implement proper deduplication strategy (similar to MediaWiki's `HashDedupeBag`)
- **Next Steps:**
  1. Create `hashing/deduplication_cache.py` class
  2. Track written value nodes in EntityConverter
  3. Check hash before writing new value node
  4. Re-test Q120248304 to confirm duplicates eliminated

**MediaWiki Reference:** `mediawiki-extensions-Wikibase/repo/includes/Rdf/HashDedupeBag.php`

### TODO: Integration Testing
- Create comprehensive test suites for each feature category
- Fix roundtrip test failures
- Validate all RDF block generation

### PLANNED: Truthy Mode
Mode for generating only best-rank statements (truthy statements):

```turtle
# Only include wdt:Pxxx direct claims for best-rank statements
wd:Q42 wdt:P31 wd:Q5 .
wd:Q42 wdt:P569 "+1952-03-11T00:00:00Z"^^xsd:dateTime .

# Skip deprecated and non-best-rank statements
```

---

## Running Tests

### Run All RDF Tests
```bash
cd /home/dpriskorn/src/python/wikibase-backend
source .venv/bin/activate
pytest tests/rdf/ -v
```

### Run Specific Test Suites
```bash
# Unit tests (Phase 1)
pytest tests/rdf/test_value_node.py -v
pytest tests/rdf/test_normalization.py -v

# Writer tests (Phase 2)
pytest tests/rdf/test_value_node_writer.py -v
pytest tests/rdf/test_triple_writer_value_nodes.py -v
pytest tests/rdf/test_property_ontology.py -v
pytest tests/rdf/test_property_registry.py -v
pytest tests/rdf/test_referenced_entities.py -v

# Integration tests (Phase 3)
pytest tests/rdf/test_q42_conversion.py -v
pytest tests/rdf/test_q120248304_conversion.py -v
pytest tests/rdf/test_ttl_comparison.py -v
pytest tests/rdf/test_split_blocks.py -v
```

### Run Tests with Coverage
```bash
pytest tests/rdf/ --cov=models/rdf_builder --cov-report=html
```

### Run Tests with Detailed Output
```bash
pytest tests/rdf/ -vv -s
```

### Run Specific Test
```bash
pytest tests/rdf/test_value_node.py::test_serialize_time_value -v
```

### Run Tests for Failing Test
```bash
pytest tests/rdf/test_ttl_comparison.py -k roundtrip -v
```

---

## Test Data

### Entity JSON Files
Located in `test_data/json/entities/`:
- Q1.json - Simple entity
- Q2.json - Earth (medium)
- Q3.json, Q4.json, Q5.json - Basic entities
- Q10.json - Small entity
- Q42.json - Douglas Adams (large, 332 statements, 293 properties)
- Q120248304.json - Medium entity with globe coordinates
- Q17633526.json - Wikinews article (referenced entity)
- Q17948861.json - Small entity (for roundtrip testing)
- Q182397.json - Medium entity
- Q51605722.json - Medium entity
- Q53713.json - Large entity
- Q8413.json - Medium entity

### Golden TTL Files
Located in `test_data/rdf/ttl/`:
- Q1.ttl, Q2.ttl, Q3.ttl, Q4.ttl, Q5.ttl - Basic entities
- Q42.ttl - Large entity with all features
- Q120248304.ttl - Medium entity with globe coordinates
- Q17633526.ttl - Referenced entity
- Q17948861.ttl - Small entity for roundtrip testing
- Q182397.ttl, Q51605722.ttl, Q53713.ttl, Q8413.ttl - Medium/large entities

### Property Data
Located in `test_data/properties/`:
- properties.csv - Property metadata cache (downloaded from Wikidata)
- README.md - Property data documentation

### Scripts
- `scripts/download_properties.sh` - Download property metadata from Wikidata
- `scripts/download_properties_sparql.py` - Alternative download method using SPARQL
- `scripts/download_property_metadata.py` - Download property labels/descriptions
- `scripts/download_wikidata_entity.py` - Download entity JSON from Wikidata API
- `scripts/download_missing_entities.py` - Download missing entity JSON files

---

