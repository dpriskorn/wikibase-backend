# JSON→RDF Converter Service

## Overview

The JSON→RDF Converter service is responsible for converting Wikibase JSON entity snapshots to RDF (Turtle format) using streaming generation. This service is a critical component used by both the Continuous RDF Change Streamer and Weekly RDF Dump Generator.

## Architecture

### Purpose

Convert Wikibase JSON snapshots to RDF (Turtle format) using streaming generation for efficient memory usage at 1M+ entities/week scale.

### Design Principles

1. **Streaming**: Process entities line-by-line without loading full documents in memory
2. **Efficient**: Use caching and parallel processing for optimal throughput
3. **Correct**: Follow Wikibase RDF mapping rules precisely
4. **Scalable**: Handle entities with 1000+ claims without memory issues

### Data Flow

```
Entity JSON (from S3 or API)
          ↓
    Stream JSON→RDF (Turtle)
          ↓
    Load into Graph (for diff) or Write to File (for dumps)
          ↓
    Output RDF (Turtle format)
```

## Conversion Mapping

### Wikibase RDF Mapping Rules

| JSON Field | RDF Triple Pattern | Notes |
|-----------|------------------|--------|
| Entity ID | `<entity_uri> a wikibase:Item .` | Type declaration |
| Labels | `<entity_uri> rdfs:label "label"@lang .` | One triple per language |
| Descriptions | `<entity_uri> schema:description "description"@lang .` | One triple per language |
| Aliases | `<entity_uri> skos:altLabel "alias"@lang .` | One triple per alias per language |
| Claims | `<entity_uri> p:P<property> <statement_uri> .` | Link entity to statement |
| Claims | `<statement_uri> a wikibase:Statement .` | Statement type |
| Claims | `<statement_uri> ps:P<property> <value> .` | Main statement value |
| Claim Qualifiers | `<statement_uri> pq:P<qualifier> <value> .` | One triple per qualifier |
| Claim References | `<statement_uri> prov:wasDerivedFrom <ref_uri> .` | Link statement to reference |
| Reference Values | `<ref_uri> pr:P<property> <value> .` | Reference property values |
| Sitelinks | `<entity_uri> schema:sameAs <wiki_url> .` | One triple per sitelink |

## Implementation

### Streaming Approach (Critical for Scale)

```python
import json
import io
from typing import TextIO

def json_stream_to_rdf_turtle(json_input: TextIO, ttl_output: TextIO):
    """Stream JSON to RDF without loading full entity in memory"""
    
    # Write Turtle header once
    write_turtle_header(ttl_output)
    
    # Stream entities line-by-line
    line_count = 0
    triple_count = 0
    
    for line in json_input:
        entity = json.loads(line)
        entity_uri = generate_entity_uri(entity['id'])
        
        # Write entity triples immediately (don't build full string)
        ttl_output.write(f"\n# Entity: {entity['id']}\n")
        ttl_output.write(f"<{entity_uri}> a wikibase:Item .\n")
        triple_count += 1
        
        # Stream labels
        for lang, label_data in entity.get('labels', {}).items():
            label = escape_turtle(label_data['value'])
            ttl_output.write(f'<{entity_uri}> rdfs:label "{label}"@{lang} .\n')
            triple_count += 1
        
        # Stream descriptions
        for lang, desc_data in entity.get('descriptions', {}).items():
            desc = escape_turtle(desc_data['value'])
            ttl_output.write(f'<{entity_uri}> schema:description "{desc}"@{lang} .\n')
            triple_count += 1
        
        # Stream aliases
        for lang, aliases_list in entity.get('aliases', {}).items():
            for alias_data in aliases_list:
                alias = escape_turtle(alias_data['value'])
                ttl_output.write(f'<{entity_uri}> skos:altLabel "{alias}"@{lang} .\n')
                triple_count += 1
        
        # Stream claims (claim-by-claim, not all at once)
        for prop_id, claims in entity.get('claims', {}).items():
            for claim in claims:
                claim_triples = write_claim_triples(
                    ttl_output, 
                    entity_uri, 
                    prop_id, 
                    claim
                )
                triple_count += claim_triples
        
        # Stream sitelinks
        for site_key, sitelink_data in entity.get('sitelinks', {}).items():
            wiki_url = generate_wiki_url(site_key, sitelink_data['title'])
            ttl_output.write(f'<{entity_uri}> schema:sameAs <{wiki_url}> .\n')
            triple_count += 1
        
        ttl_output.write(f"\n# --- End entity: {entity['id']} ---\n\n")
        
        # Flush periodically (every 1000 triples)
        if triple_count % 1000 == 0:
            ttl_output.flush()
        
        line_count += 1
        
        # Log progress
        if line_count % 100 == 0:
            logging.info(f"Processed {line_count} entities, {triple_count} triples")


def write_turtle_header(output: TextIO):
    """Write Turtle prefix declarations"""
    output.write("""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <http://schema.org/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .
@prefix p: <http://www.wikidata.org/prop/> .
@prefix ps: <http://www.wikidata.org/prop/statement/> .
@prefix pq: <http://www.wikidata.org/prop/qualifier/> .
@prefix pr: <http://www.wikidata.org/prop/reference/> .
@prefix wikibase: <http://wikiba.se/ontology#> .

""")
```

### Claim Writing Implementation

```python
def write_claim_triples(output: TextIO, entity_uri: str, prop_id: str, claim: dict) -> int:
    """Write claim triples to output, return triple count"""
    claim_id = claim.get('id')
    if not claim_id:
        return 0
    
    statement_uri = generate_statement_uri(claim_id)
    triple_count = 0
    
    # Write statement reference
    output.write(f'<{entity_uri}> p:{prop_id} {statement_uri} .\n')
    output.write(f'{statement_uri} a wikibase:Statement .\n')
    triple_count += 2
    
    # Write main value (mainsnak)
    main_snak = claim.get('mainsnak', {})
    snak_triples = write_snak_triples(
        output, 
        statement_uri, 
        'ps', 
        prop_id, 
        main_snak
    )
    triple_count += snak_triples
    
    # Write rank
    rank = claim.get('rank', 'normal')
    rank_uri = f'wikibase:{rank.capitalize()}Rank'
    output.write(f'{statement_uri} wikibase:rank {rank_uri} .\n')
    triple_count += 1
    
    # Write qualifiers
    qualifiers = claim.get('qualifiers', {})
    for qual_prop_id, qualifiers_list in qualifiers.items():
        for qualifier in qualifiers_list:
            qual_triples = write_snak_triples(
                output, 
                statement_uri, 
                'pq', 
                qual_prop_id, 
                qualifier
            )
            triple_count += qual_triples
    
    # Write references
    references = claim.get('references', [])
    for ref_idx, reference in enumerate(references):
        ref_uri = generate_reference_uri(statement_uri, ref_idx)
        
        # Link statement to reference
        output.write(f'{statement_uri} prov:wasDerivedFrom {ref_uri} .\n')
        triple_count += 1
        
        # Write reference values
        ref_snaks = reference.get('snaks', {})
        for ref_prop_id, ref_snaks_list in ref_snaks.items():
            for ref_snak in ref_snaks_list:
                ref_triples = write_snak_triples(
                    output, 
                    ref_uri, 
                    'pr', 
                    ref_prop_id, 
                    ref_snak
                )
                triple_count += ref_triples
    
    return triple_count


def write_snak_triples(
    output: TextIO, 
    subject_uri: str, 
    prefix: str, 
    prop_id: str, 
    snak: dict
) -> int:
    """Write snak triples (mainsnak, qualifier, or reference)"""
    snaktype = snak.get('snaktype', 'value')
    
    if snaktype == 'novalue':
        output.write(f'<{subject_uri}> {prefix}:{prop_id} wikibase:noValue .\n')
        return 1
    
    elif snaktype == 'somevalue':
        output.write(f'<{subject_uri}> {prefix}:{prop_id} wikibase:someValue .\n')
        return 1
    
    elif snaktype == 'value':
        datavalue = snak.get('datavalue', {})
        datatype = snak.get('datatype', 'string')
        
        return write_datavalue_triples(
            output, 
            subject_uri, 
            prefix, 
            prop_id, 
            datatype, 
            datavalue
        )
    
    return 0


def write_datavalue_triples(
    output: TextIO, 
    subject_uri: str, 
    prefix: str, 
    prop_id: str, 
    datatype: str, 
    datavalue: dict
) -> int:
    """Write datavalue triples based on datatype"""
    value_type = datavalue.get('type')
    
    if value_type == 'string':
        value = escape_turtle(datavalue['value'])
        output.write(f'<{subject_uri}> {prefix}:{prop_id} "{value}" .\n')
        return 1
    
    elif value_type == 'wikibase-entityid':
        entity_id = datavalue['value']['id']
        entity_uri = generate_entity_uri(entity_id)
        output.write(f'<{subject_uri}> {prefix}:{prop_id} <{entity_uri}> .\n')
        return 1
    
    elif value_type == 'monolingualtext':
        text = escape_turtle(datavalue['value']['text'])
        lang = datavalue['value']['language']
        output.write(f'<{subject_uri}> {prefix}:{prop_id} "{text}"@{lang} .\n')
        return 1
    
    elif value_type == 'time':
        time_value = parse_time_value(datavalue['value'])
        output.write(f'<{subject_uri}> {prefix}:{prop_id} "{time_value}"^^xsd:dateTime .\n')
        return 1
    
    elif value_type == 'quantity':
        amount = datavalue['value']['amount']
        unit = datavalue['value'].get('unit', 'http://www.wikidata.org/entity/Q199')
        output.write(f'<{subject_uri}> {prefix}:{prop_id} {amount}^^xsd:decimal .\n')
        return 1
    
    elif value_type == 'globecoordinate':
        coord = format_coordinate(datavalue['value'])
        output.write(f'<{subject_uri}> {prefix}:{prop_id} "{coord}"^^geo:geoJSONLiteral .\n')
        return 1
    
    else:
        logging.warning(f"Unknown value type: {value_type}")
        return 0
```

### URI Generation

```python
def generate_entity_uri(entity_id: str) -> str:
    """Generate entity URI"""
    return f"http://www.wikidata.org/entity/{entity_id}"


def generate_statement_uri(claim_guid: str) -> str:
    """Generate statement URI from claim GUID"""
    return f"http://www.wikidata.org/entity/statement/{claim_guid}"


def generate_reference_uri(statement_uri: str, ref_index: int) -> str:
    """Generate reference URI"""
    return f"{statement_uri}-{ref_index:09d}#ref"


def generate_wiki_url(site_key: str, title: str) -> str:
    """Generate wiki URL from sitelink"""
    # Map site keys to URLs
    site_map = {
        'enwiki': 'https://en.wikipedia.org/wiki/',
        'dewiki': 'https://de.wikipedia.org/wiki/',
        'commonswiki': 'https://commons.wikimedia.org/wiki/',
    }
    
    base = site_map.get(site_key, f'https://{site_key}.org/wiki/')
    encoded_title = title.replace(' ', '_')
    return f"{base}{encoded_title}"
```

### Turtle Escaping

```python
import re

def escape_turtle(value: str) -> str:
    """Escape special characters for Turtle format"""
    # Escape backslashes first
    value = value.replace('\\', '\\\\')
    
    # Escape quotes
    value = value.replace('"', '\\"')
    
    # Escape newlines, tabs, returns
    value = value.replace('\n', '\\n')
    value = value.replace('\r', '\\r')
    value = value.replace('\t', '\\t')
    
    # Escape other control characters
    value = re.sub(r'[\x00-\x1F\x7F]', lambda m: f'\\u{ord(m.group()):04X}', value)
    
    return value
```

### Time Value Parsing

```python
def parse_time_value(time_data: dict) -> str:
    """Parse Wikibase time value to ISO 8601 format"""
    time_str = time_data['time']
    precision = time_data['precision']
    
    # Remove +00:00 timezone if present
    if time_str.endswith('+00:00'):
        time_str = time_str[:-6]
    
    # Truncate based on precision
    if precision >= 11:  # 1 day or more precise
        return f"{time_str}Z"
    elif precision == 10:  # 1 month
        return f"{time_str[:7]}-01T00:00:00Z"
    elif precision == 9:  # 1 year
        return f"{time_str[:5]}-01-01T00:00:00Z"
    elif precision == 8:  # 10 years
        return f"{time_str[:4]}0-01-01T00:00:00Z"
    elif precision == 7:  # 100 years
        return f"{time_str[:3]}00-01-01T00:00:00Z"
    else:
        return f"{time_str[:2]}000-01-01T00:00:00Z"
```

## Optimizations

### 1. Prefix Caching

```python
TURTLE_PREFIXES = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <http://schema.org/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .
@prefix p: <http://www.wikidata.org/prop/> .
@prefix ps: <http://www.wikidata.org/prop/statement/> .
@prefix pq: <http://www.wikidata.org/prop/qualifier/> .
@prefix pr: <http://www.wikidata.org/prop/reference/> .
@prefix wikibase: <http://wikiba.se/ontology#> .

"""

# Pre-compiled templates for common patterns
ENTITY_TYPE_TEMPLATE = '{entity_uri} a wikibase:Item .\n'
LABEL_TEMPLATE = '<{entity_uri}> rdfs:label "{label}"@{lang} .\n'
DESCRIPTION_TEMPLATE = '<{entity_uri}> schema:description "{desc}"@{lang} .\n'
STATEMENT_TEMPLATE = '<{entity_uri}> p:{prop_id} {statement_uri} .\n'
STATEMENT_TYPE_TEMPLATE = '{statement_uri} a wikibase:Statement .\n'
```

### 2. Parallel Claim Conversion

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
import threading

class ThreadSafeStringIO:
    """Thread-safe StringIO for parallel claim conversion"""
    def __init__(self):
        self._buffer = StringIO()
        self._lock = threading.Lock()
    
    def write(self, text):
        with self._lock:
            self._buffer.write(text)
    
    def getvalue(self):
        with self._lock:
            return self._buffer.getvalue()
    
    def flush(self):
        with self._lock:
            self._buffer.flush()


def process_property_group(
    output: ThreadSafeStringIO, 
    entity_uri: str, 
    prop_id: str, 
    claims: list
):
    """Process all claims for a single property"""
    for claim in claims:
        write_claim_triples(output, entity_uri, prop_id, claim)


def parallel_claim_conversion(
    entity_uri: str, 
    claims_by_property: dict, 
    max_workers: int = 10
) -> str:
    """Convert claims in parallel by property"""
    output = ThreadSafeStringIO()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_property_group, 
                output, 
                entity_uri, 
                prop_id, 
                claims
            )
            for prop_id, claims in claims_by_property.items()
        ]
        
        # Wait for all futures to complete
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error processing property group: {e}")
    
    return output.getvalue()
```

### 3. Buffered Writing

```python
class BufferedTurtleWriter:
    """Buffered writer for improved I/O performance"""
    
    def __init__(self, output: TextIO, buffer_size: int = 8192):
        self.output = output
        self.buffer_size = buffer_size
        self._buffer = []
        self._buffer_len = 0
    
    def write(self, text: str):
        """Write to buffer, flush if buffer is full"""
        self._buffer.append(text)
        self._buffer_len += len(text)
        
        if self._buffer_len >= self.buffer_size:
            self.flush()
    
    def flush(self):
        """Flush buffer to output"""
        if self._buffer:
            self.output.write(''.join(self._buffer))
            self._buffer = []
            self._buffer_len = 0
            self.output.flush()


def convert_with_buffering(
    json_input: TextIO, 
    turtle_output: TextIO, 
    buffer_size: int = 8192
):
    """Convert JSON to Turtle with buffered writing"""
    writer = BufferedTurtleWriter(turtle_output, buffer_size)
    
    write_turtle_header(writer)
    
    for line in json_input:
        entity = json.loads(line)
        # Write triples to buffered writer
        # ... conversion logic ...
    
    writer.flush()  # Ensure all data is written
```

### 4. Claim Pre-sorting

```python
def sort_claims_by_complexity(entity: dict) -> dict:
    """Sort claims by complexity for better parallel processing"""
    claims = entity.get('claims', {})
    
    # Calculate complexity score for each property
    property_complexity = {}
    for prop_id, claim_list in claims.items():
        total_complexity = 0
        for claim in claim_list:
            # Count qualifiers
            qualifiers = len(claim.get('qualifiers', {}))
            # Count references
            refs = len(claim.get('references', []))
            total_complexity += 1 + qualifiers + refs
        
        property_complexity[prop_id] = total_complexity
    
    # Sort properties by complexity (lightest first)
    sorted_props = sorted(
        claims.items(), 
        key=lambda x: property_complexity[x[0]]
    )
    
    return dict(sorted_props)
```

## Graph Loading

### For Diff Computation

```python
import rdflib

def load_rdf_into_graph(turtle_data: str) -> rdflib.Graph:
    """Load RDF Turtle data into rdflib Graph for diff computation"""
    graph = rdflib.Graph()
    graph.parse(data=turtle_data, format='turtle')
    return graph


def compute_graph_diff(
    from_graph: rdflib.Graph, 
    to_graph: rdflib.Graph
) -> tuple:
    """Compute diff between two graphs"""
    added_triples = list(set(to_graph) - set(from_graph))
    deleted_triples = list(set(from_graph) - set(to_graph))
    
    # Handle large entities (>10K triples)
    total_triples = len(added_triples) + len(deleted_triples)
    if total_triples > 10000:
        logging.warning(f"Large diff: {total_triples} triples, consider import mode")
        return None, None  # Signal for import mode
    
    return added_triples, deleted_triples


def triples_to_turtle(triples: list) -> str:
    """Convert list of triples to Turtle format"""
    output = StringIO()
    
    for s, p, o in triples:
        # Format subject
        subject = format_node(s)
        predicate = format_node(p)
        object_ = format_node(o)
        
        output.write(f'{subject} {predicate} {object_} .\n')
    
    return output.getvalue()


def format_node(node) -> str:
    """Format RDF node as Turtle string"""
    if isinstance(node, rdflib.URIRef):
        return f'<{str(node)}>'
    elif isinstance(node, rdflib.Literal):
        value = escape_turtle(str(node.value))
        if node.language:
            return f'"{value}"@{node.language}'
        elif node.datatype:
            return f'"{value}"^^{node.datatype.n3()}'
        else:
            return f'"{value}"'
    elif isinstance(node, rdflib.BNode):
        return f'_{str(node)}'
    else:
        return str(node)
```

## Configuration

| Option | Description | Default |
|---------|-------------|---------|
| `buffer_size` | Write buffer size in bytes | 8192 |
| `flush_interval` | Flush after N triples | 1000 |
| `max_workers` | Parallel claim conversion workers | 10 |
| `parallel_claims` | Enable parallel claim conversion | true |
| `prefix_cache_enabled` | Cache prefix declarations | true |
| `validate_output` | Validate RDF syntax | false |
| `format` | Output RDF format | turtle |
| `include_metadata` | Include conversion metadata | true |

## Error Handling

### Syntax Validation

```python
from rdflib import Graph

def validate_turtle_syntax(turtle_data: str) -> tuple:
    """Validate Turtle syntax"""
    graph = Graph()
    
    try:
        graph.parse(data=turtle_data, format='turtle')
        return True, None
    except Exception as e:
        return False, str(e)


def safe_convert_with_validation(
    json_input: TextIO, 
    turtle_output: TextIO, 
    validate: bool = True
):
    """Convert with optional validation"""
    # Capture output for validation
    temp_output = StringIO()
    
    # Perform conversion
    try:
        json_stream_to_rdf_turtle(json_input, temp_output)
    except Exception as e:
        logging.error(f"Conversion failed: {e}")
        raise
    
    # Validate if enabled
    if validate:
        turtle_data = temp_output.getvalue()
        is_valid, error = validate_turtle_syntax(turtle_data)
        
        if not is_valid:
            logging.error(f"Validation failed: {error}")
            raise ValueError(f"Invalid Turtle syntax: {error}")
        
        # Write to final output
        turtle_output.write(turtle_data)
    else:
        # Stream directly without validation
        turtle_output.write(temp_output.getvalue())
```

### Error Recovery

```python
def convert_with_error_recovery(
    json_input: TextIO, 
    turtle_output: TextIO, 
    error_log_path: str
):
    """Convert entities, logging errors for problematic entities"""
    error_log = open(error_log_path, 'w', encoding='utf-8')
    
    processed_count = 0
    error_count = 0
    
    for line_num, line in enumerate(json_input, 1):
        entity_id = None
        try:
            entity = json.loads(line)
            entity_id = entity.get('id', 'unknown')
            
            # Convert entity to Turtle
            turtle_output.write(f"# Entity: {entity_id}\n")
            convert_entity_to_turtle(entity, turtle_output)
            turtle_output.write("\n")
            
            processed_count += 1
            
        except json.JSONDecodeError as e:
            error_count += 1
            error_log.write(
                f"JSON Error at line {line_num}: {e}\n"
                f"Content: {line[:200]}...\n\n"
            )
        except Exception as e:
            error_count += 1
            error_log.write(
                f"Conversion error for {entity_id} at line {line_num}: {e}\n"
            )
            
            # Continue processing other entities
            continue
    
    error_log.close()
    
    logging.info(f"Processed {processed_count} entities")
    logging.warning(f"Encountered {error_count} errors, see {error_log_path}")
```

## Monitoring and Metrics

### Key Metrics

```
# Conversion metrics
json_rdf_converter_entities_processed_total[counter]
json_rdf_converter_triples_generated_total[counter]
json_rdf_converter_conversion_duration_seconds[summary]
json_rdf_converter_entity_size_bytes[histogram]

# Performance metrics
json_rdf_converter_buffer_flushes_total[counter]
json_rdf_converter_parallel_workers_active[gauge]
json_rdf_converter_cache_hits_total[counter]
json_rdf_converter_cache_misses_total[counter]

# Error metrics
json_rdf_converter_conversion_errors_total[counter]
json_rdf_converter_validation_errors_total[counter]
```

### Example Metrics (Prometheus format)

```python
from prometheus_client import Counter, Histogram, Summary, Gauge

# Conversion metrics
entities_processed = Counter('json_rdf_converter_entities_processed_total', 'Entities converted')
triples_generated = Counter('json_rdf_converter_triples_generated_total', 'Triples generated')
conversion_duration = Summary('json_rdf_converter_conversion_duration_seconds', 'Conversion time')
entity_size = Histogram('json_rdf_converter_entity_size_bytes', 'Entity size', buckets=[1000, 10000, 100000, 1000000])

# Performance metrics
buffer_flushes = Counter('json_rdf_converter_buffer_flushes_total', 'Buffer flushes')
active_workers = Gauge('json_rdf_converter_parallel_workers_active', 'Active parallel workers')
cache_hits = Counter('json_rdf_converter_cache_hits_total', 'Cache hits')
cache_misses = Counter('json_rdf_converter_cache_misses_total', 'Cache misses')

# Error metrics
conversion_errors = Counter('json_rdf_converter_conversion_errors_total', 'Conversion errors')
validation_errors = Counter('json_rdf_converter_validation_errors_total', 'Validation errors')
```

### Performance Tracking

```python
import time
from functools import wraps

def track_performance(metric):
    """Decorator to track function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            metric.observe(duration)
            return result
        return wrapper
    return decorator


@track_performance(conversion_duration)
def convert_entity_to_turtle(entity: dict, output: TextIO):
    """Convert entity with performance tracking"""
    # Conversion logic
    pass
```

## Testing

### Unit Tests

```python
import pytest

def test_label_conversion():
    """Test label conversion"""
    entity = {
        "id": "Q42",
        "labels": {
            "en": {"language": "en", "value": "Douglas Adams"},
            "de": {"language": "de", "value": "Douglas Adams"}
        }
    }
    
    output = StringIO()
    convert_entity_to_turtle(entity, output)
    turtle_data = output.getvalue()
    
    assert '<http://www.wikidata.org/entity/Q42> rdfs:label "Douglas Adams"@en .' in turtle_data
    assert '<http://www.wikidata.org/entity/Q42> rdfs:label "Douglas Adams"@de .' in turtle_data


def test_claim_conversion():
    """Test claim conversion"""
    entity = {
        "id": "Q42",
        "claims": {
            "P31": [
                {
                    "mainsnak": {
                        "datatype": "wikibase-item",
                        "datavalue": {"value": {"id": "Q5"}, "type": "wikibase-entityid"},
                        "property": "P31",
                        "snaktype": "value"
                    },
                    "id": "q42$ABCD1234",
                    "rank": "normal"
                }
            ]
        }
    }
    
    output = StringIO()
    convert_entity_to_turtle(entity, output)
    turtle_data = output.getvalue()
    
    # Check statement reference
    assert 'p:P31 <http://www.wikidata.org/entity/statement/q42$ABCD1234>' in turtle_data
    
    # Check statement type
    assert '<http://www.wikidata.org/entity/statement/q42$ABCD1234> a wikibase:Statement .' in turtle_data
    
    # Check main value
    assert 'ps:P31 <http://www.wikidata.org/entity/Q5>' in turtle_data


def test_escaping():
    """Test Turtle string escaping"""
    test_string = 'Quote " and \\ backslash'
    escaped = escape_turtle(test_string)
    
    assert escaped == 'Quote \\" and \\\\ backslash'


def test_time_value_parsing():
    """Test time value parsing"""
    time_data = {
        "time": "+1952-03-11T00:00:00Z",
        "precision": 11,
        "timezone": 0
    }
    
    parsed = parse_time_value(time_data)
    assert parsed == "1952-03-11T00:00:00Z"
```

### Integration Tests

```python
def test_end_to_end_conversion():
    """Test complete conversion pipeline"""
    # Load sample entity
    with open('test_data/Q42.json', 'r') as f:
        entity = json.load(f)
    
    # Convert to Turtle
    output = StringIO()
    convert_entity_to_turtle(entity, output)
    turtle_data = output.getvalue()
    
    # Validate syntax
    graph = Graph()
    graph.parse(data=turtle_data, format='turtle')
    
    # Verify triples
    assert len(graph) > 0
    
    # Check for expected entity
    entity_uri = URIRef('http://www.wikidata.org/entity/Q42')
    assert (entity_uri, None, None) in graph


def test_large_entity_conversion():
    """Test conversion of entity with many claims"""
    # Create entity with 1000 claims
    entity = create_test_entity(num_claims=1000)
    
    output = StringIO()
    convert_entity_to_turtle(entity, output)
    turtle_data = output.getvalue()
    
    # Should not cause memory issues
    assert len(turtle_data) > 0
    
    # Validate
    graph = Graph()
    graph.parse(data=turtle_data, format='turtle')
    assert len(graph) > 1000
```

## Deployment

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY json_rdf_converter/ .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV MAX_WORKERS=10

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Expose metrics endpoint
EXPOSE 8080

# Run application
CMD ["python", "-m", "json_rdf_converter.server"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: json-rdf-converter
spec:
  replicas: 3
  selector:
    matchLabels:
      app: json-rdf-converter
  template:
    metadata:
      labels:
        app: json-rdf-converter
    spec:
      containers:
      - name: converter
        image: json-rdf-converter:latest
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: MAX_WORKERS
          value: "10"
        - name: BUFFER_SIZE
          value: "8192"
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Service Definition

```yaml
apiVersion: v1
kind: Service
metadata:
  name: json-rdf-converter
spec:
  selector:
    app: json-rdf-converter
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```

## Performance Benchmarks

### Expected Performance

| Metric | Small Entity | Medium Entity | Large Entity |
|--------|-------------|---------------|--------------|
| Claims | < 50 | 50-500 | > 500 |
| Triples | < 200 | 200-2000 | > 2000 |
| Conversion Time | < 10ms | 10-100ms | 100-1000ms |
| Memory | < 1MB | 1-10MB | 10-50MB |

### Throughput Targets

| Configuration | Entities/sec | Triples/sec | Memory |
|-------------|---------------|--------------|---------|
| Single-threaded | 100 | 1000 | 100MB |
| 10 workers | 1000 | 10000 | 500MB |
| 50 workers | 5000 | 50000 | 2GB |

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) - Core architecture principles
- [CHANGE-DETECTION-RDF-GENERATION.md](CHANGE-DETECTION-RDF-GENERATION.md) - RDF generation architecture
- [ENTITY-MODEL.md](ENTITY-MODEL.md) - Entity model documentation
- [RDF-DIFF-STRATEGY.md](RDF-DIFF-STRATEGY.md) - RDF diff strategy documentation
- [WEEKLY-RDF-DUMP-GENERATOR.md](WEEKLY-RDF-DUMP-GENERATOR.md) - Weekly dump service
- [CONTINUOUS-RDF-CHANGE-STREAMER.md](CONTINUOUS-RDF-CHANGE-STREAMER.md) - Continuous RDF streamer
