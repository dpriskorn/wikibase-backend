# RDF Diff Strategy

## Approach: Full Convert + Diff

This strategy fully converts both revisions to RDF and computes a diff between them.

## Why This Approach

- **Simpler implementation** - Use proven RDF diff libraries (Jena RDF Patch, RDF4J)
- **Better reliability** - Correctness more important than efficiency when dealing with 1B+ entities
- **Faster iteration** - Easier to debug and extend
- **Streaming approach mitigates memory** - Convert both revisions to RDF with streaming (line-by-line), then diff using memory-efficient algorithms

Rejected alternative (JSON→RDF operation mapping) is extremely error-prone at Wikibase scale:
- Entities have complex nested structures (claims, qualifiers, references)
- Edge cases are hard - claim removal affects references, qualifier changes affect multiple triples
- No efficiency gain - With streaming RDF conversion, you're reading the full JSON anyway to generate complete RDF
- Mapping bugs corrupt data - If you miss converting a dependent triple, downstream consumers get inconsistent state

## Implementation Flow

1. Stream from_snapshot JSON → RDF (Turtle, line-by-line)
2. Stream to_snapshot JSON → RDF (Turtle, line-by-line)
3. Load both RDF documents using in-memory graph structure
4. Compute RDF diff (library handles graph comparison)
5. Emit rdf_change event with added/deleted triples

## Key Technique

Don't hold full entity RDF strings in memory. Use RDF graph data structures (e.g., Jena's in-memory graph) that can handle diffing efficiently.

## Handling Very Large Entities

If an entity has > 10K triples:

1. Emit operation: import for the to_revision instead of diff (full replacement)
2. Let consumer handle the merge (effectively a full replace)

This hybrid approach provides best of both worlds when entities are extremely large.
