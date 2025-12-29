# Internal representation of all Wikibase objects

## 1. Canonical architecture (Hybrid, done right)

```
Wikibase JSON
     ↓
Strict JSON Parser
     ↓
Semantic IR (internal representation)
     ↓
┌──────────────────────────┐
│        RDF Pipeline      │
│                          │
│  ┌──────────────┐        │
│  │ Truthy RDF   │──────▶ wdt: graph
│  ├──────────────┤        │
│  │ Full RDF     │──────▶ p/ps/pq/pr graph
│  └──────────────┘        │
└──────────────────────────┘
```

**Key property:**
➡️ *Each entity is parsed once, normalized once, emitted twice.*

---

## 2. Internal Representation (IR): the keystone

Do **not** mirror Wikibase JSON.
Do **not** mirror Wikibase PHP objects.

### 2.1 Entity IR

```python
class Entity:
    id: str               # Q42 / P31
    type: Literal["item", "property"]
    labels: dict[str, str]
    descriptions: dict[str, str]
    aliases: dict[str, list[str]]
    statements: list[Statement]
    sitelinks: Optional[dict[str, dict[str, Any]]  # Site links to other wikis
```

---

### 2.2 Statement IR

```python
class Statement:
    property: str         # P31
    value: Value
    rank: Literal["preferred", "normal", "deprecated"]
    qualifiers: list[Qualifier]
    references: list[Reference]
    statement_id: str     # e.g., "Q42-F078E5B3-F9A8-480E-B7AC-D97778CBBEF9"
```

➡️ Statement IDs are required for RDF generation to construct wds: URIs matching Wikidata pattern.

---

### 2.3 Qualifier IR

```python
class Qualifier:
    property: str
    value: Value
```

➡️ Qualifiers are key-value pairs that modify statement values.

---

### 2.4 Reference IR

```python
class ReferenceValue:
    property: str
    value: Value

class Reference:
    hash: str                    # e.g., "a4d108601216cffd2ff1819ccf12b483486b62e7"
    snaks: list[ReferenceValue]  # Flat list of (property, value) pairs
```

➡️ Reference hashes are required for RDF generation to construct wdref: URIs matching Wikidata pattern.

---

### 2.5 Value IR (this matters most)

```python
class Value:
    kind: Literal[
        "entity",
        "string",
        "time",
        "quantity",
        "globe",
        "monolingual",
        "external_id",
        "commons_media",
        "geo_shape",
        "tabular_data",
        "musical_notation",
        "url",
        "math",
        "entity_schema"
    ]
    value: Any
    datatype_uri: str
```

Examples:

* entity → `"Q5"` → `wd:Q5`
* string → literal string value
* time → normalized ISO string + precision
* quantity → decimal + unit URI
* globe → lat/long + globe URI
* monolingual → language + text pair
* external_id → external identifier string
* commons_media → Commons file reference
* geo_shape → geographic map data
* tabular_data → tabular data reference
* musical_notation → LilyPond notation
* url → HTTP/HTTPS URL
* math → LaTeX mathematical expression
* entity_schema → entity schema reference

---

## 3. JSON → IR: deterministic, lossy by design

### What you intentionally drop

| JSON concept | Reason                        |
| ------------ | ----------------------------- |
| map ordering | RDF is unordered              |
| empty maps   | meaningless                   |

Note: Statement IDs and reference hashes are retained for RDF generation to construct wds: and wdref: URIs matching Wikidata pattern.

### Parsing example (P31)

```python
for stmt_json in claims["P31"]:
    if stmt_json["mainsnak"]["snaktype"] != "value":
        continue

    stmt = Statement(
        property="P31",
        value=parse_value(stmt_json["mainsnak"]),
        rank=stmt_json["rank"],
        qualifiers=parse_qualifiers(stmt_json),
        references=parse_references(stmt_json),
        statement_id=stmt_json["id"],
    )
```

---

## 4. RDF pipeline design

### 4.1 Emitters are stateless

```python
class RdfEmitter:
    def emit_entity(self, entity: Entity): ...
```

No shared mutable state.
No global caches.

---

## 5. Truthy RDF emitter (wdt:)

### Semantics (match Wikidata)

* Exclude deprecated
* Preferred beats normal
* If no preferred → use normal

### Implementation sketch

```python
def emit_truthy(entity):
    by_prop = group_by_property(entity.statements)

    for prop, stmts in by_prop.items():
        chosen = select_truthy(stmts)
        for stmt in chosen:
            emit(
                wd(entity.id),
                wdt(prop),
                stmt.value.to_rdf()
            )
```

This gives:

* compact graphs
* excellent query performance
* compatibility with most consumers

---

## 6. Full RDF emitter (p/ps/pq/pr)

### Statement node strategy (important)

Use statement ID from Wikidata JSON to construct deterministic URIs matching Wikidata RDF pattern.

Example:

```python
stmt_node = URI(f"{Vocab.WDS}{stmt.statement_id}")
```

This produces URIs like `http://www.wikidata.org/entity/statement/Q42-F078E5B3-F9A8-480E-B7AC-D97778CBBEF9`, matching the `wds:` prefix in Wikidata RDF.

---

### Emission sketch

```python
stmt_node = URI(f"{Vocab.WDS}{stmt.statement_id}")

emit(wd(e.id), p(prop), stmt_node)
emit(stmt_node, ps(prop), value)

emit(stmt_node, wikibase:rank, stmt.rank)

for q in stmt.qualifiers:
    emit(stmt_node, pq(q.property), q.value)

for ref in stmt.references:
    ref_node = URI(f"{Vocab.WDREF}{ref.hash}")
    emit(stmt_node, prov:wasDerivedFrom, ref_node)
```

---

## 7. Vocabulary layer (do this early)

Single source of truth:

```python
class Vocab:
    WD   = "http://www.wikidata.org/entity/"
    WDT  = "http://www.wikidata.org/prop/direct/"
    P    = "http://www.wikidata.org/prop/"
    PS   = "http://www.wikidata.org/prop/statement/"
    PQ   = "http://www.wikidata.org/prop/qualifier/"
    PR   = "http://www.wikidata.org/prop/reference/"
    WDS  = "http://www.wikidata.org/entity/statement/"
    WDREF = "http://www.wikidata.org/reference/"
```

Emitters never hardcode URIs.

---

## 8. Output strategy (backend-grade)

### Strongly recommended

* N-Triples
* gzip streams
* one file per shard

```
entities/Q42.nt.gz
entities/Q43.nt.gz
```

or

```
shard=Q000–Q999/
```

---

## 9. Change streams (design now, thank yourself later)

Your IR enables:

```
old IR ─┐
        ├─ diff ─▶ RDF delta
new IR ─┘
```

You cannot do this reliably with JSON or PHP serializers.

---

## 10. Compatibility story (important)

You should aim for:

| Feature                | Compatible      |
| ---------------------- | --------------- |
| wdt: triples           | ✅               |
| RDF vocabulary         | ✅               |
| entity URIs            | ✅               |
| exact statement hashes | ❌ (intentional) |
| blank node IDs         | ❌               |

This is a **feature**, not a bug.

---

## 11. What you’ve effectively replaced

| Wikibase          | Your backend       |
| ----------------- | ------------------ |
| SerializerFactory | JSON → IR          |
| EntityRdfBuilder  | IR → RDF           |
| MediaWiki runtime | Stateless pipeline |
| PHP objects       | Typed IR           |

---

## 12. Final sanity check

If someone asked:

> “How do you build RDF?”

Your answer should be:

> “We normalize Wikibase JSON into a semantic IR and emit both truthy and full RDF from that.”

That’s a **modern, scalable answer**.