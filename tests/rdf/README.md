# RDF Serialization Test Suite

## Overview

Comprehensive test suite for JSON → RDF Turtle serialization based on Wikibase PHP tests.

## Test Structure

```
tests/rdf/
├── fixtures.py              # Test fixtures (load JSON/RDF data)
├── conftest.py             # Pytest fixtures
├── test_01_dataset_metadata.py
├── test_02_labels.py
├── test_03_descriptions.py
├── test_04_aliases.py
├── test_05_direct_properties.py
├── test_06_statement_structure.py
├── test_07_values_basic.py
├── test_08_values_wikibase_item.py
├── test_09_values_monolingualtext.py
├── test_10_values_time.py
├── test_11_values_quantity.py
├── test_12_values_coordinates.py
├── test_13_values_external_id.py
├── test_14_novalue.py
└── ... (more coming)
```

## Test Categories

### 1. Core Structure (1 test)
- Dataset metadata (data:, schema:Dataset, version, dateModified)

### 2. Labels & Descriptions & Aliases (3 tests)
- Single and multi-language labels
- Single and multi-language descriptions  
- Single and multi-language aliases

### 3. Direct Properties (1 test)
- wd:P2 wd:Q42, wdno:P3 (novalue)

### 4. Statement Structure (4 tests)
- Statement URI generation
- Statement types (wikibase:Statement, wikibase:BestRank)
- Ranks (NormalRank, PreferredRank, DeprecatedRank)

### 5. Basic Value Types (4 tests)
- String, External-ID, URL, Wikibase-item

### 6. Complex Value Types (4 tests)
- Monolingualtext, Time, Quantity, Globe coordinates

### 7. Special Values (2 tests)
- Commons media, Novalue

## Test Data Sources

### PHP Test Entities (copied from Wikibase)
Located in: `test_data/entities/`

- P2 - Property definition
- Q1 - Simple entity (no labels)
- Q2 - Labels, descriptions, aliases
- Q3 - Sitelinks
- Q4 - Full statements with all datatypes
- Q5 - Badges and sitelinks
- Q6 - Qualifiers
- Q7 - References
- Q8 - Bad dates
- Q9 - Redirect
- Q10 - Redirect with foreign source properties

### Wikidata Real Entities
Located in: `test_data/entities/`

- Q42 - Douglas Adams (complex real entity) + expected TTL
- Q17948861 - Simple test entity + expected TTL
- Q120248304 - Test with references

## Expected RDF Files (copied from PHP tests)
Located in: `test_data/expected_rdf/`

Subdirectories:
- `statements/` - Statement structure tests (Q4_statements.nt, etc.)
- `values/` - Value node tests (Q4_values.nt)
- `qualifiers/` - Qualifier tests (Q6_qualifiers.nt)
- `references/` - Reference tests (Q7_references.nt)
- `sitelinks/` - Sitelink tests (Q3_sitelinks.nt)
- `terms/` - Labels/descriptions/aliases tests (Q2_terms.nt)
- `properties/` - Property definition tests (P2_all.nt)
- `referenced/` - Referenced entity tests (Q4_referenced.nt)

- `statements/` - Statement structure tests
- `values/` - Value node tests
- `qualifiers/` - Qualifier tests
- `references/` - Reference tests
- `sitelinks/` - Sitelink tests
- `terms/` - Labels/descriptions/aliases tests
- `properties/` - Property definition tests

## Test Strategy

### Phase 1: Basic Tests (Current Focus)
1. Get existing serialization to work
2. Add missing basic features (aliases, qualifiers, references)
3. Fix value types (time, quantity, coordinates)
4. Add proper value nodes (psv:, pqv:, prv:)
5. Run tests and fix failures

### Phase 2: Advanced Features
5. Property definitions
6. Referenced entities
7. Complex integration scenarios

## Current Issues Identified

Based on Wikibase PHP tests, current serializer misses:

1. **Aliases** - No skos:altLabel generation
2. **Qualifiers** - Only hardcoded P805, missing full qualifier support
3. **References** - No prov:wasDerivedFrom, no reference nodes
4. **Value nodes** - No wdv:, psv:, pqv:, prv: structured values
5. **Time values** - Missing precision, timezone, calendar model metadata
6. **Quantity values** - Missing unit, upperbound, lowerbound
7. **Coordinate values** - Missing globe, precision metadata
8. **Proper rank handling** - Always uses NormalRank, missing Preferred/Deprecated
9. **Property definitions** - Hardcoded, should be dynamic
10. **NoValue handling** - Missing wdno: triples with OWL restrictions
11. **Referenced entities** - Missing labels/descriptions for Q42, Q666, etc.

## Running Tests

```bash
# Run all RDF tests
pytest tests/rdf/ -v

# Run specific test
pytest tests/rdf/test_02_labels.py -v

# Run with detailed output
pytest tests/rdf/test_02_labels.py::test_q2_single_label_en -vv
```

## Next Steps

1. ✅ Copy PHP test data and expected RDF - DONE
2. ✅ Create test infrastructure fixtures - DONE
3. �️ Create 30+ basic tests - IN PROGRESS
4. �️ Fix serializer issues as tests fail
5. �️ Add value nodes (psv:, pqv:, prv:)
6. �️ Add qualifiers support
7. �️ Add references support
8. �️ Add aliases support
9. �️ Add property definitions
10. �️ Complex integration tests

## Resources

- Wikibase PHP tests: `mediawiki-extensions-Wikibase/repo/tests/phpunit/data/rdf/`
- Datatypes reference: `WIKIDATA/DATATYPES.md`
- RDF Properties reference: `WIKIDATA/RDF-PROPERTIES.md`
