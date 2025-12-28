# RDF Test Suite Summary

## What Was Done

### 1. Copied PHP Test Data from Wikibase
✅ All test entities copied from `mediawiki-extensions-Wikibase/repo/tests/phpunit/data/rdf/entities/`
- Q1-Q11 (PHP test entities covering all features)
- P2 (property definition)
- Q42, Q17948861, Q120248304 (real Wikidata entities)

### 2. Copied Expected RDF Files
✅ All expected NT files copied to `test_data/expected_rdf/`
- `statements/` - 39+ statement structure tests
- `values/` - Value node tests
- `qualifiers/` - Qualifier tests
- `references/` - Reference tests
- `sitelinks/` - Sitelink tests
- `terms/` - Labels/descriptions/aliases tests
- `properties/` - Property definition tests

### 3. Organized Test Data Structure
```
test_data/
├── entities/          # JSON input files
│   ├── P2.json
│   ├── Q1-Q11.json   # PHP test entities
│   ├── Q42.json      # Real Wikidata
│   └── Q17948861.json
├── expected_rdf/      # Expected RDF output
│   ├── statements/
│   ├── values/
│   ├── qualifiers/
│   ├── references/
│   ├── sitelinks/
│   ├── terms/
│   ├── properties/
│   └── referenced/
├── errors/           # Error test cases
└── revisions/        # Revision test data
```

### 4. Created Test Infrastructure
✅ `tests/rdf/fixtures.py` - Test utilities
- `load_json_entity(entity_id)` - Load JSON entity
- `serialize_entity(entity)` - Convert to RDF Turtle
- `normalize_turtle()` - Normalize for comparison
- `load_expected_rdf()` - Load expected RDF files

✅ `tests/rdf/conftest.py` - Pytest fixtures
- `api_client()` - Test client
- `base_url()` - API base URL

### 5. Created 14 Test Files
✅ test_01_dataset_metadata.py - Dataset metadata
✅ test_02_labels.py - Label triples (rdfs:label, skos:prefLabel, schema:name)
✅ test_03_descriptions.py - Description triples (schema:description)
✅ test_04_aliases.py - Alias triples (skos:altLabel)
✅ test_05_direct_properties.py - wd:P2 wd:Q42 triples
✅ test_06_statement_structure.py - Statement URIs, types, ranks
✅ test_07_values_basic.py - String, External-ID, URL values
✅ test_08_values_wikibase_item.py - wd:Q42 entity references
✅ test_09_values_monolingualtext.py - Text + language values
✅ test_10_values_time.py - Time with precision, timezone, calendar
✅ test_11_values_quantity.py - Amount + unit + bounds
✅ test_12_values_coordinates.py - Lat + lon + globe + precision
✅ test_13_values_commons_media.py - Special:FilePath URLs
✅ test_14_novalue.py - wdno:P3 triples

## Test Coverage by Category

| Category | Tests | Status |
|----------|--------|--------|
| Core Structure | 1 | ✅ Created |
| Labels/Descriptions/Aliases | 3 | ✅ Created |
| Direct Properties | 1 | ✅ Created |
| Statement Structure | 4 | ✅ Created |
| Basic Values | 4 | ✅ Created |
| Complex Values | 4 | ✅ Created |
| Special Values | 2 | ✅ Created |
| Qualifiers | 0 | ⏳ Pending |
| References | 0 | ⏳ Pending |
| Sitelinks | 0 | ⏳ Pending |
| Property Definitions | 0 | ⏳ Pending |
| Referenced Entities | 0 | ⏳ Pending |
| Complex Integration | 0 | ⏳ Pending |
| **Total** | **19** | **14 done, 5 pending** |

## Current Serializer Issues

Based on Wikibase PHP tests, these features are missing:

1. ❌ **Aliases** - No skos:altLabel generation
2. ❌ **Qualifiers** - Only hardcoded P805, missing full support
3. ❌ **References** - No prov:wasDerivedFrom, no reference nodes
4. ❌ **Value Nodes** - No wdv:, psv:, pqv:, prv: structured values
5. ❌ **Time Metadata** - Missing precision, timezone, calendar model
6. ❌ **Quantity Metadata** - Missing unit, upperbound, lowerbound
7. ❌ **Coordinate Metadata** - Missing globe, precision
8. ❌ **Rank Handling** - Always NormalRank, missing Preferred/Deprecated
9. ❌ **Property Definitions** - Hardcoded, should be dynamic
10. ❌ **NoValue** - Missing wdno: triples with OWL restrictions
11. ❌ **Referenced Entities** - Missing labels for Q42, Q666, etc.

## Next Steps

### Phase 1: Fix Basic Features (Priority)
1. Run existing 14 tests
2. Fix aliases support (test_04)
3. Fix rank handling (test_06)
4. Fix novalue handling (test_14)
5. Fix basic value types

### Phase 2: Add Value Nodes
6. Implement psv: (statement value nodes)
7. Implement pqv: (qualifier value nodes)
8. Implement prv: (reference value nodes)

### Phase 3: Add Qualifiers & References
9. Add full qualifier support
10. Add full reference support
11. Add prov:wasDerivedFrom

### Phase 4: Complex Features
12. Property definitions
13. Referenced entities
14. Sitelinks
15. Complex integration tests

## Running Tests

```bash
# Run all RDF tests
pytest tests/rdf/ -v

# Run specific test
pytest tests/rdf/test_02_labels.py -v

# Run with details
pytest tests/rdf/test_02_labels.py::test_q2_single_label_en -vv

# Run and show output
pytest tests/rdf/test_02_labels.py -vv -s
```

## Test Data Reference

### PHP Test Entities
| Entity | Purpose | Key Features |
|---------|---------|--------------|
| Q1 | Simple entity | No labels, no claims |
| Q2 | Labels/aliases | Multi-language labels, descriptions, aliases |
| Q3 | Sitelinks | enwiki, ruwiki sitelinks |
| Q4 | Full features | All datatypes, ranks, statements |
| Q5 | Badges | Sitelinks with badges |
| Q6 | Qualifiers | Statements with qualifiers |
| Q7 | References | Statements with references |
| Q8 | Bad dates | Invalid date values |
| Q9 | Redirect | Redirect entity |
| Q10 | Redirect complex | Redirect with foreign source properties |
| P2 | Property | Property definition |

### Expected RDF Files
Each entity has multiple expected NT files for different features:
- `Q2_terms.nt` - Labels, descriptions, aliases
- `Q4_statements.nt` - Statement structure
- `Q6_qualifiers.nt` - Qualifier structure
- `Q7_references.nt` - Reference structure
- `P2_all.nt` - Property definition
- etc.
