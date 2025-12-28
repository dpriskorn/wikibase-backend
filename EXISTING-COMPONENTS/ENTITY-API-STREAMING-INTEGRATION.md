# Entity-API Streaming Integration

## Overview

This document describes how to integrate the Python entity-api with WMF's Scala streaming-updater-producer for RDF streaming to Kafka.

---

## MediaWiki/Wikibase RDF Format

Wikibase (the MediaWiki extension powering Wikidata) provides RDF data via the EntityData endpoint.

### EntityData Endpoint

**URL Pattern**: `/wiki/Special:EntityData/{entity_id}.ttl`

**Example**: `https://www.wikidata.org/wiki/Special:EntityData/Q42.ttl`

**Supported Formats**: Turtle, JSON-LD, N-Triples, RDF/XML
- Default format: Turtle (`.ttl`)
- MIME type: `text/turtle`

### RDF Structure (Turtle Format)

Based on analysis of MediaWiki/Wikibase test data:

```turtle
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix wikibase: <http://wikiba.se/ontology-beta#> .
@prefix wdata: <https://test.wikidata.org/wiki/Special:EntityData/> .
@prefix wd: <http://test.wikidata.org/entity/> .
@prefix wds: <http://test.wikidata.org/entity/statement/> .
@prefix wdref: <http://test.wikidata.org/reference/> .
@prefix wdv: <http://test.wikidata.org/value/> .
@prefix wdt: <http://test.wikidata.org/prop/direct/> .
@prefix p: <http://test.wikidata.org/prop/> .
@prefix ps: <http://test.wikidata.org/prop/statement/> .
@prefix psv: <http://test.wikidata.org/prop/statement/value/> .
@prefix pq: <http://test.wikidata.org/prop/qualifier/> .
@prefix pqv: <http://test.wikidata.org/prop/qualifier/value/> .
@prefix pr: <http://test.wikidata.org/prop/reference/> .
@prefix prv: <http://test.wikidata.org/prop/reference/value/> .
@prefix wdno: <http://test.wikidata.org/prop/novalue/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix schema: <http://schema.org/> .
@prefix cc: <http://creativecommons.org/ns#> .
@prefix geo: <http://www.opengis.net/ont/geosparql#> .
@prefix prov: <http://www.w3.org/ns/prov#> .

# Item
wd:Q42 a wikibase:Item ;
  rdfs:label "Douglas Adams"@en ;
  skos:prefLabel "Douglas Adams"@en ;
  schema:name "Douglas Adams"@en .

# Property
wdt:P31 wds:Q5-623409b4-4857-528e-dc7a-dbadd8a8ff43 a wikibase:Statement ;
  ps:P31 <http://www.wikidata.org> ;
  wikibase:rank wikibase:NormalRank,
    wikibase:BestRank .
```

### Key Entity Types

**Items**: `wd:Q{num} a wikibase:Item`
- Example: `wd:Q42 a wikibase:Item`

**Properties**: `wdt:P{num} a wikibase:Property`
- Example: `wdt:P31 a wikibase:Property`

### Value Types

**Simple Values**:
```turtle
wdt:P21 <http://www.wikidata.org> .
```

**Quantity Values** (for properties like P63 "population"):
```turtle
wdt:P63 "150000"^^xsd:decimal .
```

**Time Values** (for properties like P268 "point in time"):
```turtle
wdt:P268 "2013-01-01T00:00:00Z"^^xsd:dateTime ;
  psv:P268 wdv:5ecc8d72111da6fbcc582342d3205365 ;
  wikibase:rank wikibase:NormalRank,
    wikibase:BestRank .
```

**Coordinate Values** (for properties like P625 "coordinate location"):
```turtle
wdt:P625 "Point(32.715 -117.1625)"^^geo:wktLiteral ;
```

**Statement Values** (for complex statement data):
```turtle
wds:Q10-623409b4-4857-528e-dc7a-dbadd8a8ff43 a wikibase:Statement ;
  ps:P31 <http://www.wikidata.org> ;
  wikibase:rank wikibase:NormalRank,
    wikibase:BestRank .
```

### Rank System

Wikibase statements use a rank system:
- `wikibase:NormalRank` - Standard rank
- `wikibase:PreferredRank` - Preferred for same property
- `wikibase:BestRank` - Best value for same property
- `wikibase:DeprecatedRank` - Superseded value

---

## Integration Approaches

### Option A: HTTP Proxy Service (Simplest)

Create a Python/FastAPI service that translates MediaWiki EntityData API calls to entity-api calls.

**Architecture**:
```
streaming-updater-producer (Scala/Flink)
    → HTTP GET /wiki/Special:EntityData/Q42.ttl
    → Python Proxy (FastAPI)
        → HTTP GET /entity/Q42/latest
        → entity-api (FastAPI)
```

**Python Proxy Implementation**:
```python
from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/wiki/Special:EntityData/{entity_id}.ttl")
async def get_entity_data(entity_id: str):
    response = requests.get(f"http://entity-api:8000/entity/{entity_id}/latest")
    entity_data = response.json()["data"]
    turtle = convert_json_to_turtle(entity_data)
    return Response(content=turtle, media_type="text/turtle")
```

**Pros**:
- No changes to streaming-updater-producer Scala code
- Fast to implement
- Easy to debug
- Clean separation of concerns

**Cons**:
- Extra network hop
- Need JSON→Turtle conversion in Python
- Adds latency to pipeline

### Option B: Modify Streaming-Updater-Producer (Complex)

Change the Scala/Java code in streaming-updater-producer to call entity-api HTTP endpoints directly.

**Changes Required**:
1. Modify `WikibaseRepository` HTTP client to call `http://entity-api:8000/entity/{id}/latest`
2. Convert JSON response to RDF using rdflib or existing WMF code
3. Update configuration for entity-api hostname

**Code Changes**:
```scala
// Instead of:
val uris = new WikibaseRepository.Uris(
  new URI(s"https://${hostname}"),
  entityNamespaces,
  WikibaseRepository.Uris.DEFAULT_ENTITY_DATA_PATH,
  entityDataFormat,
  httpClientConfig,
  clock
)

// Use:
val uris = new WikibaseRepository.Uris(
  new URI("http://entity-api:8000"),
  entityNamespaces,
  "/entity/{id}/latest",
  "application/json",
  httpClientConfig,
  clock
)
```

**Pros**:
- Direct HTTP calls, no proxy
- Can reuse existing JSON→RDF conversion code
- Lower latency

**Cons**:
- Requires Scala/Java knowledge
- Needs rdflib dependency or custom conversion
- More complex to test locally

### Option C: Entity-API Provides MediaWiki Endpoints (Cleanest)

Add MediaWiki-compatible EntityData endpoints to entity-api that output Turtle RDF.

**Architecture**:
```
streaming-updater-producer (Scala/Flink)
    → HTTP GET /wiki/Special:EntityData/Q42.ttl
    → entity-api (FastAPI)
        → GET /entity/Q42/latest (returns JSON)
        → Converts to Turtle using rdflib
        → Returns Turtle response
```

**Entity-API Implementation**:
```python
from fastapi import FastAPI
from rdflib import Graph
import json

@app.get("/wiki/Special:EntityData/{entity_id}.ttl")
async def get_entity_data(entity_id: str, oldid: str = None, format: str = "json"):
    # Fetch entity from S3
    entity = get_entity_from_s3(entity_id, oldid)
    
    # Convert to Turtle using rdflib
    g = Graph()
    # ... convert entity to RDF triples ...
    
    if format == "json":
        return Response(content=g.serialize(format="json-ld"), media_type="application/ld+json")
    else:  # default to turtle
        return Response(content=g.serialize(format="turtle"), media_type="text/turtle")
```

**Pros**:
- Cleanest architecture
- streaming-updater-producer works as-is
- Entity-api becomes complete solution
- No external services needed

**Cons**:
- Most work required (implement full RDF serialization)
- Larger Docker image (rdflib + dependencies)
- More complex to implement and test

---

## Integration Strategy Questions

### Question 1: Entity Fetch Approach

Which approach for entity-api integration?

**A. HTTP Proxy Service** - Create separate proxy service, easiest to implement
**B. Modify Streaming-Updater-Producer** - Change Scala code to call entity-api directly
**C. Entity-API Provides MediaWiki Endpoints** - Add Turtle output to entity-api, streaming-updater-producer unchanged

### Question 2: RDF Serialization Library

For entity-api Turtle output (Option C):

**A. Use rdflib** - Mature library, follows standards, but adds ~15MB to Docker image
**B. Custom Implementation** - More control, lighter, but more work
**C. Reuse WMF Code** - Copy RDF serialization code from MediaWiki/Wikibase (complex, language mismatch)

### Question 3: Flink Architecture

For running streaming-updater-producer in Docker:

**A. Embedded Mini-Cluster** - Single container, simpler setup, harder to debug Flink jobs
**B. Full Flink Cluster** - JobManager + TaskManager services, production-like, easier to debug

---

## Next Steps

1. **Decide integration approach** - Choose A, B, or C
2. **Decide RDF serialization** - Choose rdflib, custom, or WMF code reuse
3. **Decide Flink architecture** - Choose embedded or full cluster
4. **Implement chosen solution** - Create Dockerfiles, update docker-compose.yml, test integration
5. **End-to-end testing** - Verify full pipeline: entity-api → Kafka → streaming-updater-producer → RDF Kafka
