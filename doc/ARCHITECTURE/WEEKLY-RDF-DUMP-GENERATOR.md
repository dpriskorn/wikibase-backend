# Weekly RDF Dump Generator

## Overview

The Weekly RDF Dump Generator is responsible for generating weekly dumps of all entities in both JSON and RDF formats as standalone S3 files. This service provides complete snapshots of the Wikibase knowledge base for archival, distribution, and bulk import purposes.

## Architecture

### Purpose

Generate weekly dumps of all entities in both JSON and RDF formats as standalone S3 files.

### Design Decision

**Weekly dumps are FILES, not Kafka events.** The `rdf_change` schema is NOT used for weekly dumps - use standard Turtle format directly.

### Data Flow

```
Weekly Scheduler (Cron/Airflow)
          ↓
     Query entity_head: Get all entities
          ↓
     Batch fetch S3 snapshots (parallel, 1000s at a time)
          ↓
     ┌──────────────────────────────────┐
     ↓                              ↓
Convert to JSON Dump           Convert to RDF (Turtle) - Streaming
     ↓                              ↓
Write to S3:                     Write to S3:
  dump/YYYY-MM-DD/full.json       dump/YYYY-MM-DD/full.ttl
  (optional partitioned)          (optional partitioned)
```

## Implementation Design

### Step 1: Query Changed Entities

```sql
SELECT DISTINCT h.entity_id, h.head_revision_id, h.updated_at
FROM entity_head h
WHERE h.updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY h.updated_at ASC;
```

### Step 2: Batch Fetch S3 Snapshots

```python
from concurrent.futures import ThreadPoolExecutor
import boto3

s3_client = boto3.client('s3')

def fetch_snapshots_in_batches(entities, batch_size=1000):
    """Fetch S3 snapshots in parallel batches"""
    for batch_start in range(0, len(entities), batch_size):
        batch = entities[batch_start:batch_start + batch_size]
        
        # Build S3 URIs
        uris = [
            f"s3://{bucket}/{entity_id}/r{revision_id}.json"
            for entity_id, revision_id in batch
        ]
        
        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(fetch_snapshot, entity_id, revision_id)
                for entity_id, revision_id in batch
            ]
            snapshots = [future.result() for future in futures]
        
        # Yield batch for processing
        yield zip(batch, snapshots)


def fetch_snapshot(entity_id, revision_id, bucket="wikibase-revisions"):
    """Fetch single snapshot from S3"""
    key = f"{entity_id}/r{revision_id}.json"
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read().decode('utf-8'))
```

### Step 3: Generate JSON Dump

#### JSON Dump Format

```json
{
  "dump_metadata": {
    "generated_at": "2025-01-15T00:00:00Z",
    "time_range": "2025-01-08T00:00:00Z/2025-01-15T00:00:00Z",
    "entity_count": 1234567,
    "format": "canonical-json"
  },
  "entities": [
    {
      "entity": { 
        "id": "Q42",
        "type": "item",
        "labels": {
          "en": { "language": "en", "value": "Douglas Adams" }
        },
        "descriptions": {
          "en": { "language": "en", "value": "English writer and humorist" }
        },
        "claims": { ... }
      },
      "metadata": {
        "revision_id": 327,
        "entity_id": "Q42",
        "s3_uri": "s3://bucket/Q42/r327.json",
        "updated_at": "2025-01-15T10:30:00Z"
      }
    },
    ...
  ]
}
```

#### JSON Dump Implementation

```python
import json
import gzip
from datetime import datetime, timezone

def generate_json_dump(entities, output_path, compress=True):
    """Generate JSON dump file"""
    metadata = {
        "dump_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "time_range": f"{get_week_start().isoformat()}/{datetime.now(timezone.utc).isoformat()}",
            "entity_count": len(entities),
            "format": "canonical-json"
        },
        "entities": []
    }
    
    # Build entities list
    for entity_id, entity_json, revision_id in entities:
        metadata["entities"].append({
            "entity": entity_json,
            "metadata": {
                "revision_id": revision_id,
                "entity_id": entity_id,
                "s3_uri": f"s3://wikibase-revisions/{entity_id}/r{revision_id}.json",
                "updated_at": entity_json.get("modified")
            }
        })
    
    # Write to file
    if compress:
        output_path = f"{output_path}.gz"
        with gzip.open(output_path, 'wt', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    return output_path
```

### Step 4: Generate RDF Dump

#### RDF Dump Format (Turtle)

```turtle
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <http://schema.org/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix p: <http://www.wikidata.org/prop/direct/> .
@prefix ps: <http://www.wikidata.org/prop/statement/> .
@prefix pq: <http://www.wikidata.org/prop/qualifier/> .
@prefix wikibase: <http://wikiba.se/ontology#> .

# Dump metadata
[] a schema:DataDownload ;
    schema:dateModified "2025-01-15T00:00:00Z"^^xsd:dateTime ;
    schema:temporalCoverage "2025-01-08T00:00:00Z/2025-01-15T00:00:00Z" ;
    schema:numberOfItems 1234567 ;
    dcat:downloadURL <https://s3.amazonaws.com/wikibase-dumps/2025-01-15/full.ttl> ;
    schema:encodingFormat "text/turtle" ;
    schema:name "Wikibase Weekly RDF Dump" .

# Entity Q42
wd:Q42 a wikibase:Item ;
    rdfs:label "Douglas Adams"@en ;
    rdfs:label "Douglas Adams"@de ;
    schema:description "English writer and humorist"@en ;
    p:P31 wd:Q5 ;
    p:P569 "1952-03-11"^^xsd:date ;
    p:P570 "2001-05-11"^^xsd:date .

# Entity Q123
wd:Q123 a wikibase:Item ;
    ...
```

#### RDF Dump Implementation (Streaming)

```python
import gzip
from datetime import datetime, timezone

def generate_rdf_dump_streaming(entities, output_path, compress=True):
    """Generate RDF Turtle dump using streaming to avoid memory issues"""
    
    # Determine output file
    if compress:
        output_path = f"{output_path}.gz"
        opener = gzip.open
        mode = 'wt'
    else:
        opener = open
        mode = 'w'
    
    with opener(output_path, mode, encoding='utf-8') as f:
        # Write Turtle header
        f.write("""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <http://schema.org/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix p: <http://www.wikidata.org/prop/direct/> .
@prefix ps: <http://www.wikidata.org/prop/statement/> .
@prefix pq: <http://www.wikidata.org/prop/qualifier/> .
@prefix wikibase: <http://wikiba.se/ontology#> .

""")
        
        # Write dump metadata
        now = datetime.now(timezone.utc).isoformat()
        week_start = get_week_start().isoformat()
        entity_count = len(entities)
        
        f.write(f"""# Dump metadata
[] a schema:DataDownload ;
    schema:dateModified "{now}"^^xsd:dateTime ;
    schema:temporalCoverage "{week_start}/{now}" ;
    schema:numberOfItems {entity_count} ;
    dcat:downloadURL <https://s3.amazonaws.com/wikibase-dumps/{now[:10]}/full.ttl> ;
    schema:encodingFormat "text/turtle" ;
    schema:name "Wikibase Weekly RDF Dump" .

""")
        
        # Stream entities
        for entity_id, entity_json, revision_id in entities:
            write_entity_to_turtle(f, entity_id, entity_json)
            f.write("\n")
    
    return output_path


def write_entity_to_turtle(output_file, entity_id, entity_json):
    """Write single entity to Turtle format"""
    entity_uri = f"wd:{entity_id}"
    
    # Entity type
    output_file.write(f"# Entity {entity_id}\n")
    output_file.write(f"{entity_uri} a wikibase:Item ;\n")
    
    # Labels
    if 'labels' in entity_json:
        for lang, label_data in entity_json['labels'].items():
            label = escape_turtle(label_data['value'])
            output_file.write(f'    rdfs:label "{label}"@{lang} ;\n')
    
    # Descriptions
    if 'descriptions' in entity_json:
        for lang, desc_data in entity_json['descriptions'].items():
            desc = escape_turtle(desc_data['value'])
            output_file.write(f'    schema:description "{desc}"@{lang} ;\n')
    
    # Aliases
    if 'aliases' in entity_json:
        for lang, aliases_list in entity_json['aliases'].items():
            for alias_data in aliases_list:
                alias = escape_turtle(alias_data['value'])
                output_file.write(f'    skos:altLabel "{alias}"@{lang} ;\n')
    
    # Claims
    if 'claims' in entity_json:
        for prop_id, claims in entity_json['claims'].items():
            for claim in claims:
                write_claim_to_turtle(output_file, entity_uri, prop_id, claim)
    
    output_file.write("    .\n")


def write_claim_to_turtle(output_file, entity_uri, prop_id, claim):
    """Write single claim to Turtle format"""
    statement_uri = generate_statement_uri(claim['id'])
    
    # Statement reference
    output_file.write(f'    p:{prop_id} {statement_uri} ;\n')
    
    # Statement type
    output_file.write(f'{statement_uri} a wikibase:Statement ;\n')
    
    # Main value
    main_snak = claim['mainsnak']
    if main_snak['datatype'] == 'wikibase-item':
        value_id = main_snak['datavalue']['value']['id']
        output_file.write(f'    ps:{prop_id} wd:{value_id} ;\n')
    elif main_snak['datatype'] == 'string':
        value = escape_turtle(main_snak['datavalue']['value'])
        output_file.write(f'    ps:{prop_id} "{value}" ;\n')
    elif main_snak['datatype'] == 'time':
        time_value = main_snak['datavalue']['value']['time']
        output_file.write(f'    ps:{prop_id} "{time_value}"^^xsd:dateTime ;\n')
    else:
        # Handle other datatypes as needed
        pass
    
    # Qualifiers
    if 'qualifiers' in claim:
        for qual_prop_id, qualifiers in claim['qualifiers'].items():
            for qualifier in qualifiers:
                write_qualifier_to_turtle(output_file, statement_uri, qual_prop_id, qualifier)
    
    # References
    if 'references' in claim:
        for ref in claim['references']:
            write_reference_to_turtle(output_file, statement_uri, ref)


def write_qualifier_to_turtle(output_file, statement_uri, qual_prop_id, qualifier):
    """Write qualifier to Turtle format"""
    # Implementation depends on qualifier structure
    pass


def write_reference_to_turtle(output_file, statement_uri, reference):
    """Write reference to Turtle format"""
    # Implementation depends on reference structure
    pass


def escape_turtle(value):
    """Escape special characters for Turtle format"""
    return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
```

### Step 5: Upload to S3

```python
import boto3

s3_client = boto3.client('s3')

def upload_dump_to_s3(local_path, s3_bucket, s3_key, metadata=None):
    """Upload dump file to S3"""
    extra_args = {
        'ContentType': 'application/json' if local_path.endswith('.json') else 'text/turtle',
        'ContentEncoding': 'gzip' if local_path.endswith('.gz') else None
    }
    
    if metadata:
        extra_args['Metadata'] = metadata
    
    s3_client.upload_file(
        local_path,
        s3_bucket,
        s3_key,
        ExtraArgs={k: v for k, v in extra_args.items() if v is not None}
    )
    
    # Generate pre-signed URL for download
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': s3_bucket, 'Key': s3_key},
        ExpiresIn=86400 * 7  # 7 days
    )
    
    return url
```

## S3 Output Structure

```
s3://wikibase-dumps/
  weekly/
    2025/
      01/
        15/
          full.json              # Complete JSON dump (compressed: full.json.gz)
          full.json.gz
          full.ttl               # Complete RDF (Turtle) dump (compressed: full.ttl.gz)
          full.ttl.gz
          part-00001.ttl         # Optional split for large datasets
          part-00001.ttl.gz
          part-00002.ttl
          part-00002.ttl.gz
          ...
          metadata.json          # Dump metadata with generation info
          manifest.txt            # Optional checksums for validation
          manifest.sha256
```

## Dump Metadata

### metadata.json Format

```json
{
  "dump_id": "2025-01-15",
  "generated_at": "2025-01-15T00:00:00Z",
  "time_range": {
    "start": "2025-01-08T00:00:00Z",
    "end": "2025-01-15T00:00:00Z"
  },
  "entity_count": 1234567,
  "format": {
    "json": {
      "file": "full.json.gz",
      "size_bytes": 543210987,
      "sha256": "abc123...",
      "entities": 1234567
    },
    "rdf": {
      "file": "full.ttl.gz",
      "size_bytes": 987654321,
      "sha256": "def456...",
      "triples": 98765432
    }
  },
  "partitioned": false,
  "compression": "gzip",
  "download_urls": {
    "json": "https://s3.amazonaws.com/wikibase-dumps/weekly/2025/01/15/full.json.gz",
    "rdf": "https://s3.amazonaws.com/wikibase-dumps/weekly/2025/01/15/full.ttl.gz"
  }
}
```

### manifest.txt Format

```
# Wikibase Weekly Dump Manifest
# Generated: 2025-01-15T00:00:00Z

full.json.gz md5 a1b2c3d4e5f6...
full.ttl.gz md5 e5f6a1b2c3d4...
metadata.json md5 1a2b3c4d5e6f...
```

## Partitioning Strategy

### Single File Approach

For smaller datasets (< 1M entities per week):
- Generate single `full.json.gz` and `full.ttl.gz`
- Simpler to download and consume

### Partitioned Approach

For larger datasets (≥ 1M entities per week):
- Split into multiple files (e.g., `part-00001.ttl.gz`, `part-00002.ttl.gz`)
- Each partition contains ~100K entities
- Include `manifest.json` with partition metadata

```python
def partition_dump(entities, partition_size=100000):
    """Partition entities into multiple dump files"""
    partitions = []
    for i in range(0, len(entities), partition_size):
        partition = entities[i:i + partition_size]
        partitions.append(partition)
    return partitions


def generate_partitioned_dump(entities, output_dir, base_filename, format='ttl'):
    """Generate partitioned dump files"""
    partitions = partition_dump(entities)
    partition_files = []
    
    for idx, partition in enumerate(partitions, start=1):
        partition_num = str(idx).zfill(5)
        filename = f"{base_filename}-part-{partition_num}.{format}"
        filepath = os.path.join(output_dir, filename)
        
        if format == 'json':
            generate_json_dump(partition, filepath)
        elif format == 'ttl':
            generate_rdf_dump_streaming(partition, filepath)
        
        partition_files.append({
            "partition": idx,
            "file": filename,
            "entity_count": len(partition)
        })
    
    return partition_files
```

## Configuration

| Option | Description | Default |
|---------|-------------|---------|
| `schedule` | Cron expression for weekly dumps | `0 2 * * 0` (Sunday 2AM) |
| `s3_source_bucket` | S3 bucket for entity snapshots | wikibase-revisions |
| `s3_dump_bucket` | S3 bucket for dumps | wikibase-dumps |
| `batch_size` | Entities per batch | 1000 |
| `parallel_workers` | Parallel conversion threads | 50 |
| `format_versions` | JSON and RDF formats to generate | `["canonical-1.0", "turtle-1.1"]` |
| `compression` | Output compression | `gzip` |
| `partition_threshold` | Entity count threshold for partitioning | 1000000 |
| `partition_size` | Entities per partition | 100000 |
| `generate_checksums` | Generate SHA256 checksums | true |
| `manifest_format` | Manifest file format | json |

## Error Handling

### Snapshot Fetch Errors

```python
def fetch_snapshots_with_retry(entities, max_retries=3):
    """Fetch snapshots with retry logic"""
    fetched = []
    failed = []
    
    for entity_id, revision_id in entities:
        for attempt in range(max_retries):
            try:
                snapshot = fetch_snapshot(entity_id, revision_id)
                fetched.append((entity_id, snapshot, revision_id))
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Failed to fetch {entity_id}/r{revision_id}: {e}")
                    failed.append((entity_id, revision_id))
                    break
                time.sleep(2 ** attempt)  # Exponential backoff
    
    return fetched, failed
```

### Dump Generation Errors

```python
def safe_generate_dump(entities, output_dir, filename):
    """Generate dump with error handling"""
    try:
        # Generate dump
        filepath = os.path.join(output_dir, filename)
        generate_rdf_dump_streaming(entities, filepath)
        
        # Verify dump
        if not verify_dump(filepath):
            raise Exception("Dump verification failed")
        
        return filepath
    except Exception as e:
        logging.error(f"Dump generation failed: {e}")
        
        # Clean up partial file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        raise
```

## Verification and Validation

### Checksum Generation

```python
import hashlib

def generate_checksum(filepath, algorithm='sha256'):
    """Generate file checksum"""
    hash_func = hashlib.new(algorithm)
    
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def verify_dump(filepath, expected_checksum=None):
    """Verify dump file integrity"""
    actual_checksum = generate_checksum(filepath)
    
    if expected_checksum:
        if actual_checksum != expected_checksum:
            raise Exception(f"Checksum mismatch: {actual_checksum} != {expected_checksum}")
    else:
        logging.info(f"Checksum for {filepath}: {actual_checksum}")
    
    return True
```

### Validation Checks

```python
def validate_json_dump(filepath):
    """Validate JSON dump structure"""
    with open(filepath, 'r', encoding='utf-8') as f:
        dump_data = json.load(f)
    
    # Check required fields
    assert 'dump_metadata' in dump_data, "Missing dump_metadata"
    assert 'entities' in dump_data, "Missing entities"
    assert 'generated_at' in dump_data['dump_metadata'], "Missing generated_at"
    assert 'entity_count' in dump_data['dump_metadata'], "Missing entity_count"
    
    # Validate entity count
    assert len(dump_data['entities']) == dump_data['dump_metadata']['entity_count'], \
        "Entity count mismatch"
    
    return True


def validate_rdf_dump(filepath):
    """Validate RDF dump syntax"""
    import rdflib
    
    graph = rdflib.Graph()
    graph.parse(filepath, format='turtle')
    
    # Check for triples
    assert len(graph) > 0, "No triples found in RDF dump"
    
    # Check for metadata
    metadata_query = """
        PREFIX schema: <http://schema.org/>
        SELECT ?dateModified WHERE {
            ?x schema:dateModified ?dateModified
        }
    """
    results = graph.query(metadata_query)
    assert len(results) > 0, "Missing dump metadata"
    
    return True
```

## Monitoring and Metrics

### Key Metrics

```
# Dump generation
weekly_dump_generation_duration_seconds[summary]
weekly_dump_entities_processed_total[counter]
weekly_dump_bytes_generated_total[counter]
weekly_dump_triples_generated_total[counter]

# S3 operations
weekly_dump_s3_upload_duration_seconds[summary]
weekly_dump_s3_upload_bytes_total[counter]

# Errors
weekly_dump_generation_failed_total[counter]
weekly_dump_upload_failed_total[counter]

# Validation
weekly_dump_validation_duration_seconds[summary]
weekly_dump_validation_passed_total[counter]
weekly_dump_validation_failed_total[counter]
```

### Example Metrics (Prometheus format)

```python
from prometheus_client import Counter, Histogram, Summary

# Generation metrics
generation_duration = Summary('weekly_dump_generation_duration_seconds', 'Dump generation time')
entities_processed = Counter('weekly_dump_entities_processed_total', 'Total entities processed')
bytes_generated = Counter('weekly_dump_bytes_generated_total', 'Total bytes generated')
triples_generated = Counter('weekly_dump_triples_generated_total', 'Total triples generated')

# S3 metrics
upload_duration = Summary('weekly_dump_s3_upload_duration_seconds', 'S3 upload time')
upload_bytes = Counter('weekly_dump_s3_upload_bytes_total', 'Total bytes uploaded')

# Error metrics
generation_failed = Counter('weekly_dump_generation_failed_total', 'Failed dump generations')
upload_failed = Counter('weekly_dump_upload_failed_total', 'Failed S3 uploads')

# Validation metrics
validation_duration = Summary('weekly_dump_validation_duration_seconds', 'Validation time')
validation_passed = Counter('weekly_dump_validation_passed_total', 'Passed validations')
validation_failed = Counter('weekly_dump_validation_failed_total', 'Failed validations')
```

## Scheduling

### Cron Job

```bash
# Weekly dump generation - Sunday 2AM UTC
0 2 * * 0 /usr/local/bin/weekly-dump-generator --config /etc/wikibase/dump-config.yml
```

### Airflow DAG

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'wikibase',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'weekly_rdf_dump',
    default_args=default_args,
    description='Generate weekly RDF dumps',
    schedule_interval='0 2 * * 0',  # Sunday 2AM UTC
    catchup=False,
    max_active_runs=1,
)

generate_dump = BashOperator(
    task_id='generate_weekly_dump',
    bash_command='/usr/local/bin/weekly-dump-generator --config /etc/wikibase/dump-config.yml',
    dag=dag,
)
```

## Performance Optimization

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_fetch_and_convert(entities, max_workers=50):
    """Fetch and convert entities in parallel"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all fetch tasks
        future_to_entity = {
            executor.submit(fetch_snapshot, entity_id, revision_id): (entity_id, revision_id)
            for entity_id, revision_id in entities
        }
        
        # Collect results as they complete
        fetched_entities = []
        for future in as_completed(future_to_entity):
            entity_id, revision_id = future_to_entity[future]
            try:
                snapshot = future.result()
                fetched_entities.append((entity_id, snapshot, revision_id))
            except Exception as e:
                logging.error(f"Failed to fetch {entity_id}: {e}")
    
    return fetched_entities
```

### Memory Optimization

```python
def streaming_rdf_generation(entities, output_path, batch_size=10000):
    """Generate RDF in batches to reduce memory usage"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header once
        write_turtle_header(f)
        
        # Process entities in batches
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            
            # Write batch
            for entity_id, entity_json, revision_id in batch:
                write_entity_to_turtle(f, entity_id, entity_json)
            
            # Flush periodically
            f.flush()
            
            # Log progress
            logging.info(f"Processed {min(i + batch_size, len(entities))}/{len(entities)} entities")
```

## Retention Policy

### S3 Lifecycle Rules

```json
{
  "Rules": [
    {
      "ID": "WeeklyDumpRetention",
      "Status": "Enabled",
      "Prefix": "weekly/",
      "Transitions": [
        {
          "TransitionDays": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "TransitionDays": 90,
          "StorageClass": "GLACIER"
        },
        {
          "TransitionDays": 180,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

### Retention Configuration

| Age | Storage Class | Cost |
|-----|---------------|------|
| 0-30 days | Standard | $0.023/GB |
| 30-90 days | Standard-IA | $0.0125/GB |
| 90-180 days | Glacier | $0.004/GB |
| 180-365 days | Deep Archive | $0.00099/GB |
| 365+ days | Expired | - |

## Testing

### Unit Tests

```python
def test_json_dump_generation():
    """Test JSON dump generation"""
    entities = [
        ("Q42", sample_entity_json, 327)
    ]
    
    output_file = generate_json_dump(entities, "/tmp/test.json", compress=False)
    
    # Validate structure
    with open(output_file, 'r') as f:
        dump_data = json.load(f)
    
    assert dump_data['dump_metadata']['entity_count'] == 1
    assert len(dump_data['entities']) == 1
    assert dump_data['entities'][0]['entity']['id'] == 'Q42'


def test_rdf_dump_generation():
    """Test RDF dump generation"""
    entities = [
        ("Q42", sample_entity_json, 327)
    ]
    
    output_file = generate_rdf_dump_streaming(entities, "/tmp/test.ttl", compress=False)
    
    # Validate Turtle syntax
    graph = rdflib.Graph()
    graph.parse(output_file, format='turtle')
    
    assert len(graph) > 0
```

### Integration Tests

```python
def test_end_to_end_dump_generation():
    """Test complete dump generation pipeline"""
    # Fetch entities
    entities = fetch_recent_entities()
    
    # Generate JSON dump
    json_file = generate_json_dump(entities, "/tmp/weekly.json")
    
    # Generate RDF dump
    rdf_file = generate_rdf_dump_streaming(entities, "/tmp/weekly.ttl")
    
    # Upload to S3
    json_url = upload_dump_to_s3(json_file, "test-bucket", "weekly/2025/01/15/full.json.gz")
    rdf_url = upload_dump_to_s3(rdf_file, "test-bucket", "weekly/2025/01/15/full.ttl.gz")
    
    # Verify downloads
    assert json_url is not None
    assert rdf_url is not None
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
COPY weekly_dump_generator/ .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Create output directory
RUN mkdir -p /tmp/dumps

# Health check
HEALTHCHECK --interval=5m --timeout=30s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run application
CMD ["python", "-m", "weekly_dump_generator.main"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: CronJob
metadata:
  name: weekly-rdf-dump-generator
spec:
  schedule: "0 2 * * 0"  # Sunday 2AM UTC
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: dump-generator
            image: weekly-rdf-dump-generator:latest
            env:
            - name: S3_SOURCE_BUCKET
              value: "wikibase-revisions"
            - name: S3_DUMP_BUCKET
              value: "wikibase-dumps"
            - name: LOG_LEVEL
              value: "INFO"
            - name: PARTITION_THRESHOLD
              value: "1000000"
            resources:
              requests:
                memory: "4Gi"
                cpu: "1000m"
              limits:
                memory: "8Gi"
                cpu: "2000m"
            volumeMounts:
            - name: tmp-dumps
              mountPath: /tmp/dumps
          volumes:
          - name: tmp-dumps
            emptyDir:
              sizeLimit: 50Gi
          restartPolicy: OnFailure
          backoffLimit: 3
```

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) - Core architecture principles
- [STORAGE-ARCHITECTURE.md](STORAGE-ARCHITECTURE.md) - S3 + Vitess storage model
- [CHANGE-DETECTION-RDF-GENERATION.md](CHANGE-DETECTION-RDF-GENERATION.md) - RDF generation architecture
- [ENTITY-MODEL.md](ENTITY-MODEL.md) - Entity model documentation
- [RDF-DIFF-STRATEGY.md](RDF-DIFF-STRATEGY.md) - RDF diff strategy documentation
