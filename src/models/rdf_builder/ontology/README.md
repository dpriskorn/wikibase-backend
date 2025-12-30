# Ontology

Defines Wikibase RDF ontology mappings and property shape generation based on datatypes.

## Components

- **datatypes.py**: Property shape factory
  - `property_shape()`: Creates `PropertyShape` objects based on datatype
  - Maps Wikidata datatypes to RDF predicate structures

- **wikibase.py**: Wikibase predicate URI generator
  - `wikibase_predicates()`: Returns standard Wikibase predicate URIs

## Property Shape Generation

The `property_shape()` function creates property configurations for RDF generation:

### Simple Types (no value node)
For these datatypes, values are written directly as literals or URIs:
- wikibase-item
- string
- external-id
- monolingualtext

These generate standard predicates:
- `wdt:{pid}` - direct claim
- `ps:{pid}` - statement value
- `pq:{pid}` - qualifier
- `pr:{pid}` - reference

### Complex Types (with value node)
For these datatypes, values require intermediate value nodes:
- time
- globe-coordinate

These add an extra predicate:
- `psv:{pid}` - statement value node

## Usage

```python
from models.rdf_builder.ontology.datatypes import property_shape

# Simple type
shape = property_shape("P31", "wikibase-item")
# shape.predicates.value_node is None

# Complex type
shape = property_shape("P569", "time")
# shape.predicates.value_node = "psv:P569"
```

## RDF Predicate Pattern

Wikibase uses multiple predicates for each property:

| Predicate | Purpose | Example |
|-----------|---------|---------|
| `wdt:P31` | Direct claims (truthy) | Item instances |
| `p:P31` | Statement links | Full statement nodes |
| `ps:P31` | Statement values | Statement data |
| `psv:P31` | Value nodes | Complex datatypes |
| `pq:P31` | Qualifiers | Statement qualifiers |
| `pr:P31` | References | Reference data |
