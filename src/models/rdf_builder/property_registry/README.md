# Property Registry

Manages Wikidata property metadata and RDF predicate mappings for RDF generation.

## Components

- **models.py**: Data models for property shapes and predicates
  - `PropertyPredicates`: RDF predicate URIs for direct, statement, qualifier, and reference triples
  - `PropertyShape`: Combines property ID, datatype, and predicate mappings

- **registry.py**: Registry that maps property IDs to their shapes
  - `PropertyRegistry`: Immutable lookup table for property metadata
  - Used by `EntityToRdfConverter` to get RDF predicates for each property

- **loader.py**: Loads property definitions from JSON files
  - `load_property_registry()`: Scans directory for `P*.json` files and builds registry

## Property Datatypes Supported

- wikibase-item
- string
- external-id
- monolingualtext
- time
- globe-coordinate

## Usage

```python
from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.property_registry.loader import load_property_registry

# Load from JSON files
registry = load_property_registry(Path("properties/"))

# Get property shape
shape = registry.shape("P31")
print(shape.predicates.direct)  # "wdt:P31"
print(shape.predicates.statement)  # "ps:P31"
```

## JSON File Format

Property JSON files must contain:
- `id`: Property ID (e.g., "P31")
- `datatype`: Wikibase datatype string

Example:
```json
{
  "id": "P31",
  "datatype": "wikibase-item"
}
```
