# RDF Builder Implementation

This document describes the RDF builder implementation for wikibase-backend, including algorithms, design decisions, and references to MediaWiki Wikibase source code.

## Overview

The RDF builder converts Wikibase entities from JSON to RDF Turtle format, producing both full and truthy RDF exports that match Wikidata's output.

## Blank Node Generation

### Algorithm

Blank node IDs for `owl:complementOf` statements are generated using MD5 hashing to ensure stability across multiple exports.

**MediaWiki Wikibase Source**: `mediawiki-extensions-Wikibase/repo/includes/Rdf/PropertySpecificComponentsRdfBuilder.php:218`

```php
$stableBNodeLabel = md5(implode('-', ['owl:complementOf', $repositoryName, $localName]));
```

**Our Implementation**:

```python
def _generate_blank_node_id(property_id: str) -> str:
    repository_name = "wikidata"
    hash_input = f"owl:complementOf-{repository_name}-{property_id}"
    return hashlib.md5(hash_input.encode()).hexdigest()
```

**Example**: For property P31, the blank node ID is `_:0b8bd71b926a65ca3fa72e5d9103e4d6`

**RDF Output**:

```turtle
wdno:P31 a owl:Class ;
    owl:complementOf _:0b8bd71b926a65ca3fa72e5d9103e4d6 .

_:0b8bd71b926a65ca3fa72e5d9103e4d6 a owl:Restriction ;
    owl:onProperty wdt:P31 ;
    owl:someValuesFrom owl:Thing .
```

## Property Predicate Structure

### Predicate Types

| Prefix | Namespace                          | Purpose                                      |
|--------|------------------------------------|----------------------------------------------|
| `wd:`   | http://www.wikidata.org/entity/      | Entity URIs                                   |
| `wdt:`  | http://www.wikidata.org/prop/direct/| Direct claim properties                       |
| `p:`    | http://www.wikidata.org/prop/       | Claim predicates                              |
| `ps:`   | http://www.wikidata.org/prop/statement/ | Statement property values            |
| `psv:`  | http://www.wikidata.org/prop/statement/value/ | Statement value nodes        |
| `pq:`   | http://www.wikidata.org/prop/qualifier/ | Qualifier predicates                   |
| `pqv:`  | http://www.wikidata.org/prop/qualifier/value/ | Qualifier value nodes        |
| `pr:`   | http://www.wikidata.org/prop/reference/ | Reference predicates                    |
| `prv:`  | http://www.wikidata.org/prop/reference/value/ | Reference value nodes    |
| `wdno:` | http://www.wikidata.org/prop/novalue/ | No-value classes for restrictions |

### Predicate Declarations

All predicate predicates (`p:`, `ps:`, `pq:`, `pr:`, `wdt:`) are declared as `owl:ObjectProperty`.

**MediaWiki Wikibase Source**: `mediawiki-extensions-Wikibase/repo/includes/Rdf/PropertySpecificComponentsRdfBuilder.php:125-158`

**Key Finding**: `psv:`, `pqv:`, and `prv:` predicates are **always** written as `owl:ObjectProperty`, regardless of property datatype.

```turtle
psv:P31 a owl:ObjectProperty .
pqv:P31 a owl:ObjectProperty .
prv:P31 a owl:ObjectProperty .
```

## Entity Metadata Loading

### Required JSON Structure

Referenced entities (e.g., Q17633526 used as a statement value) must have metadata files with the following structure:

```json
{
  "id": "Q17633526",
  "labels": {
    "en": {
      "language": "en",
      "value": "Wikinews article"
    }
  },
  "descriptions": {
    "en": {
      "language": "en",
      "value": "used with property P31"
    }
  }
}
```

**Important**: The `id` field is **required**. Without it, `parse_entity` extracts an empty string for the entity ID, causing invalid RDF output like `wd:` instead of `wd:Q17633526`.

### Metadata Download

Use the provided script to download entity metadata from Wikidata:

```bash
# Find and download all referenced entities
source .venv/bin/activate
python scripts/download_missing_entity_metadata.py
```

**Location**: `test_data/entity_metadata/{entity_id}.json`

## Implementation Files

| File | Purpose |
|------|---------|
| `src/models/rdf_builder/converter.py` | Main entity to RDF conversion orchestration |
| `src/models/rdf_builder/writers/property_ontology.py` | Property metadata and ontology generation |
| `src/models/rdf_builder/writers/triple.py` | Triple writing for entities and statements |
| `src/models/rdf_builder/property_registry/registry.py` | Property datatype and predicate management |
| `src/models/rdf_builder/entity_cache.py` | Entity metadata loading from SPARQL |

## References to MediaWiki Wikibase

### Key Files Studied

- **`PropertySpecificComponentsRdfBuilder.php`**: Blank node generation and predicate declarations
- **`RdfBuilder.php`**: Main RDF builder architecture and factory pattern
- **`RdfVocabulary.php`**: Namespace and prefix management

### Design Patterns Adopted

1. **Factory Pattern**: Multiple entity-specific RDF builders for different entity types (items, properties, lexemes)
2. **Hash-based Deduplication**: `HashDedupeBag` for efficient duplicate detection
3. **Stable Blank Nodes**: MD5-based hashing for consistent RDF exports

## Known Differences from MediaWiki Wikibase

Currently, our implementation aims to produce identical RDF output to MediaWiki Wikibase. Any intentional differences will be documented here.

None currently.
