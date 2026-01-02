# Continuous RDF Change Streamer

## Overview

The Continuous RDF Change Streamer is responsible for converting entity changes into RDF patches and streaming them continuously to downstream consumers. This service bridges the gap between change detection and RDF consumers like WDQS (Wikidata Query Service).

## Architecture

### Purpose

Convert entity changes to RDF patches and stream continuously to enable real-time updates to RDF triple stores.

### Data Flow

```
Change Detection Service (see MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md)
            ↓ (entity change events: entity_id, from_revision_id, to_revision_id)
       JSON→RDF Converter Service
            ↓
      Load both RDF representations (from and to revisions)
            ↓
      Compute RDF Diff (between two RDF graphs)
            ↓
       Emit rdf_change events (Kafka)
            ↓
   WDQS Consumer / Other Consumers
            ↓
        Apply patches to Blazegraph
```

## Services Overview

### Service 3.1: Change Event Consumer

**Purpose**: Consume entity change events from change detection service

#### Input Schema

```yaml
# Entity change event from Change Detection Service
entity_id: string                    # e.g., "Q42"
from_revision_id: integer           # Previous revision ID (null for new entities)
to_revision_id: integer             # Current revision ID
changed_at: datetime                # When the change occurred
```

#### Implementation

```python
from confluent_kafka import Consumer, KafkaError

def consume_entity_changes(kafka_config, topic):
    """Consume entity change events from change detection service"""
    consumer = Consumer(kafka_config)
    consumer.subscribe([topic])

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                raise Exception(msg.error())
        
        # Parse change event
        change_event = json.loads(msg.value())
        process_entity_change(change_event)
```

### Service 3.2: RDF Diff Computation

**Purpose**: Compute RDF diffs between two entity revisions

#### Implementation Strategy

This service uses **Option A (Full RDF Convert + Diff)** as documented in [RDF-DIFF-STRATEGY.md](RDF-DIFF-STRATEGY.md):

1. Stream from_snapshot JSON → RDF (Turtle, line-by-line)
2. Stream to_snapshot JSON → RDF (Turtle, line-by-line)
3. Load both RDF into in-memory graph structures
4. Compute RDF diff using proven library (Jena, RDF4J)
5. Return added/deleted triples

#### Algorithm

```python
def compute_rdf_diff(from_revision_json, to_revision_json):
    """Compute RDF diff between two entity revisions using Option A"""
    
    # Step 1: Convert both revisions to RDF using streaming
    from_rdf = json_to_rdf_streaming(from_revision_json)
    to_rdf = json_to_rdf_streaming(to_revision_json)
    
    # Step 2: Load into graph structures
    from_graph = rdflib.Graph()
    from_graph.parse(data=from_rdf, format='turtle')
    
    to_graph = rdflib.Graph()
    to_graph.parse(data=to_rdf, format='turtle')
    
    # Step 3: Compute diff using RDF library
    added_triples = list(set(to_graph) - set(from_graph))
    deleted_triples = list(set(from_graph) - set(to_graph))
    
    # Step 4: Handle large entities (>10K triples)
    if len(added_triples) + len(deleted_triples) > 10000:
        return None, to_rdf  # Return None for diff, full RDF for import
    
    # Step 5: Format as Turtle
    added_turtle = triples_to_turtle(added_triples)
    deleted_turtle = triples_to_turtle(deleted_triples)
    
    return added_turtle, deleted_turtle
```

#### Hybrid Optimization for Large Entities

For entities with > 10K triples, emit `operation: import` instead of `diff`:

```python
def should_use_import_mode(triple_count):
    """Determine if entity should use import mode instead of diff"""
    return triple_count > 10000

def process_large_entity(to_revision_json):
    """Process large entity by emitting import event"""
    to_rdf = json_to_rdf_streaming(to_revision_json)
    
    # Emit import event with full RDF
    emit_import_event(
        entity_id=to_revision_json['id'],
        rev_id=to_revision_json['revision'],
        rdf_data=to_rdf
    )
```

### Service 3.3: RDF Change Event Emitter

**Purpose**: Emit rdf_change events to Kafka

#### Event Schema: rdf_change/2.0.0

```yaml
$schema: /mediawiki/wikibase/entity/rdf_change/2.0.0
meta:
  uri: http://example.org/v1/mediawiki/wikibase/entity/rdf_change/12345
  dt: "2025-01-15T10:30:00Z"
  domain: wikidata.org
  request_id: abc123
  stream: wikibase.rdf_change
  topic: wikibase.rdf_change

# Entity identification
entity_id: "Q42"
rev_id: 327
operation: "diff"  # or "import"

# Sequence tracking for multi-part diffs
sequence: 0
sequence_length: 1

# RDF data (for diff operation)
rdf_added_data:
  data: |
    <http://www.wikidata.org/entity/Q42> rdfs:label "New Label"@en .
    <http://www.wikidata.org/entity/Q42> p:P31 <http://www.wikidata.org/entity/Q5> .
  mime_type: text/turtle
  size: 256
  sha1: "abc123..."

rdf_deleted_data:
  data: |
    <http://www.wikidata.org/entity/Q42> rdfs:label "Old Label"@en .
    <http://www.wikidata.org/entity/Q42> p:P31 <http://www.wikidata.org/entity/Q123> .
  mime_type: text/turtle
  size: 256
  sha1: "def456..."

# For import operation (no deleted_data)
# rdf_added_data contains full entity RDF
```

#### Implementation

```python
from confluent_kafka import Producer

def emit_rdf_change_event(producer_config, topic, change_event):
    """Emit rdf_change event to Kafka"""
    producer = Producer(producer_config)
    
    # Build event payload
    event = {
        "$schema": "/mediawiki/wikibase/entity/rdf_change/2.0.0",
        "meta": {
            "uri": f"http://{domain}/v1/mediawiki/wikibase/entity/rdf_change/{uuid.uuid4()}",
            "dt": datetime.now(timezone.utc).isoformat(),
            "domain": "wikidata.org",
            "stream": "wikibase.rdf_change",
            "topic": "wikibase.rdf_change"
        },
        "entity_id": change_event["entity_id"],
        "rev_id": change_event["rev_id"],
        "operation": change_event["operation"],
        "sequence": change_event.get("sequence", 0),
        "sequence_length": change_event.get("sequence_length", 1),
        "rdf_added_data": change_event["rdf_added_data"],
        "rdf_deleted_data": change_event.get("rdf_deleted_data")
    }
    
    # Produce to Kafka
    producer.produce(
        topic=topic,
        key=change_event["entity_id"].encode('utf-8'),
        value=json.dumps(event).encode('utf-8'),
        callback=delivery_report
    )
    producer.flush()
```

## Complete Pipeline Implementation

### End-to-End Processing

```python
def process_entity_change(change_event):
    """Process entity change and emit rdf_change event"""
    entity_id = change_event["entity_id"]
    from_rev_id = change_event["from_revision_id"]
    to_rev_id = change_event["to_revision_id"]
    
    # Step 1: Fetch both snapshots from S3
    from_snapshot = None
    to_snapshot = fetch_snapshot_from_s3(entity_id, to_rev_id)
    
    if from_rev_id:
        from_snapshot = fetch_snapshot_from_s3(entity_id, from_rev_id)
    
    # Step 2: Compute RDF diff
    if from_snapshot:
        added_turtle, deleted_turtle = compute_rdf_diff(
            from_snapshot,
            to_snapshot
        )
        
        # Check if we should use import mode
        if added_turtle is None:
            # Large entity, use import mode
            emit_rdf_change_event({
                "entity_id": entity_id,
                "rev_id": to_rev_id,
                "operation": "import",
                "rdf_added_data": {
                    "data": deleted_turtle,  # Full RDF
                    "mime_type": "text/turtle"
                }
            })
        else:
            # Normal diff mode
            emit_rdf_change_event({
                "entity_id": entity_id,
                "rev_id": to_rev_id,
                "operation": "diff",
                "rdf_added_data": {
                    "data": added_turtle,
                    "mime_type": "text/turtle"
                },
                "rdf_deleted_data": {
                    "data": deleted_turtle,
                    "mime_type": "text/turtle"
                }
            })
    else:
        # New entity, use import mode
        to_rdf = json_to_rdf_streaming(to_snapshot)
        emit_rdf_change_event({
            "entity_id": entity_id,
            "rev_id": to_rev_id,
            "operation": "import",
            "rdf_added_data": {
                "data": to_rdf,
                "mime_type": "text/turtle"
            }
        })
```

## Configuration

| Option | Description | Default |
|---------|-------------|---------|
| `input_kafka_brokers` | Kafka brokers for change events | localhost:9092 |
| `input_topic` | Input topic for entity changes | wikibase.entity_change |
| `output_kafka_brokers` | Kafka brokers for RDF changes | localhost:9092 |
| `output_topic` | Output topic for RDF changes | wikibase.rdf_change |
| `s3_bucket` | S3 bucket for snapshots | wikibase-revisions |
| `rdf_diff_library` | RDF library for diff computation | jena |
| `import_mode_threshold` | Triple count threshold for import mode | 10000 |
| `max_workers` | Parallel processing workers | 10 |
| `batch_size` | Events to process in batch | 100 |
| `compression` | Kafka compression type | gzip |
| `retries` | Max retry attempts for failed events | 3 |

## Error Handling

### Snapshot Fetch Errors

```python
def fetch_snapshot_with_retry(entity_id, revision_id, max_retries=3):
    """Fetch snapshot from S3 with retry logic"""
    for attempt in range(max_retries):
        try:
            return s3_client.get_object(
                Bucket=bucket,
                Key=f"{entity_id}/r{revision_id}.json"
            )
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to fetch snapshot for {entity_id}/r{revision_id}: {e}")
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

### RDF Diff Computation Errors

```python
def safe_compute_rdf_diff(from_snapshot, to_snapshot):
    """Compute RDF diff with error handling"""
    try:
        return compute_rdf_diff(from_snapshot, to_snapshot)
    except Exception as e:
        logging.error(f"RDF diff computation failed: {e}")
        
        # Fallback: emit import event for full entity
        to_rdf = json_to_rdf_streaming(to_snapshot)
        return None, to_rdf
```

### Kafka Production Errors

```python
def delivery_report(err, msg):
    """Callback for Kafka delivery reports"""
    if err:
        logging.error(f"Failed to deliver message: {err}")
        # Implement retry or dead letter queue logic
    else:
        logging.info(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")
```

## Monitoring and Metrics

### Key Metrics

#### Processing Metrics

```
# Event processing
rdf_streamer_events_processed_total[counter]
rdf_streamer_events_failed_total[counter]
rdf_streamer_events_import_mode_total[counter]  # Events using import mode

# Latency
rdf_streamer_end_to_end_latency_seconds[summary]
rdf_streamer_rdf_diff_computation_seconds[summary]
rdf_streamer_s3_fetch_latency_seconds[summary]

# Throughput
rdf_streamer_triples_generated_total[counter]
rdf_streamer_triples_diffed_total[counter]
```

#### Kafka Metrics

```
# Producer metrics
kafka_producer_send_latency_seconds[summary]
kafka_producer_send_failed_total[counter]
kafka_producer_retry_total[counter]

# Consumer metrics
kafka_consumer_lag_seconds[gauge]
kafka_consumer_records_processed_total[counter]
```

#### Entity Size Distribution

```
# Entity size monitoring
rdf_streamer_entity_triple_count[histogram]
rdf_streamer_entity_bytes_processed[histogram]
```

### Example Metrics (Prometheus format)

```python
from prometheus_client import Counter, Histogram, Summary

# Processing metrics
events_processed = Counter('rdf_streamer_events_processed_total', 'Total events processed')
events_failed = Counter('rdf_streamer_events_failed_total', 'Total events failed')
import_mode_used = Counter('rdf_streamer_events_import_mode_total', 'Events using import mode')

# Latency metrics
end_to_end_latency = Summary('rdf_streamer_end_to_end_latency_seconds', 'End-to-end latency')
rdf_diff_latency = Summary('rdf_streamer_rdf_diff_computation_seconds', 'RDF diff computation time')
s3_fetch_latency = Summary('rdf_streamer_s3_fetch_latency_seconds', 'S3 fetch latency')

# Size metrics
entity_triple_count = Histogram('rdf_streamer_entity_triple_count', 'Entity triple count', buckets=[100, 1000, 5000, 10000, 50000])
```

## Scaling Considerations

### Horizontal Scaling

1. **Partition by Entity ID**: Use entity_id as Kafka key for consistent routing
2. **Multiple Consumer Instances**: Deploy multiple instances with same consumer group
3. **Parallel RDF Diff**: Use worker pools for parallel diff computation

```python
from concurrent.futures import ThreadPoolExecutor

def process_events_batch(events):
    """Process events in parallel"""
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_entity_change, event) for event in events]
        results = [future.result() for future in futures]
    return results
```

### Memory Optimization

1. **Streaming RDF Conversion**: Process entities line-by-line, never load full JSON in memory
2. **Lazy RDF Graph Loading**: Only load necessary triples into memory for diff
3. **Batch Processing**: Process multiple entities in batches to amortize overhead

```python
def json_to_rdf_streaming(json_data, output_stream):
    """Stream JSON to RDF without loading full entity in memory"""
    # Process entity and write triples immediately
    for triple in generate_triples(json_data):
        output_stream.write(format_triple(triple))
        output_stream.flush()
```

### Rate Limiting

```python
from ratelimit import limits

@limits(calls=1000, period=60)  # 1000 calls per minute
def emit_rdf_change_event(event):
    """Emit event with rate limiting"""
    producer.produce(...)
```

## Performance Optimization

### Caching Strategies

1. **RDF Prefix Cache**: Cache frequently used RDF prefixes and templates
2. **Entity Metadata Cache**: Cache entity metadata to avoid repeated S3 fetches
3. **Diff Computation Cache**: Cache diff results for frequently accessed entities

```python
from functools import lru_cache

@lru_cache(maxsize=10000)
def get_entity_metadata(entity_id, revision_id):
    """Cache entity metadata"""
    return fetch_metadata_from_vitess(entity_id, revision_id)
```

### Batch Processing

```python
def batch_process_events(events, batch_size=100):
    """Process events in batches"""
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        
        # Fetch all snapshots in parallel
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(fetch_snapshot, e) for e in batch]
            snapshots = [f.result() for f in futures]
        
        # Process batch
        for event, snapshot in zip(batch, snapshots):
            process_entity_change(event, snapshot)
```

## Integration Points

### Input: Change Detection Service

Consumes entity change events from the Change Detection Service documented in [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md).

### Output: Kafka Topic

Emits `rdf_change` events to a Kafka topic for consumption by downstream services.

### Consumers

#### WDQS Consumer

The primary consumer is the WDQS (Wikidata Query Service) which applies RDF patches to Blazegraph triple store.

#### Other Potential Consumers

- Search Indexers
- Analytics Pipelines
- Mirror Services
- Custom RDF Consumers

## Testing

### Unit Tests

```python
def test_rdf_diff_computation():
    """Test RDF diff computation"""
    from_rdf = "<http://example.org/Q42> rdfs:label \"Old\"@en ."
    to_rdf = "<http://example.org/Q42> rdfs:label \"New\"@en ."
    
    added, deleted = compute_rdf_diff(from_rdf, to_rdf)
    
    assert "New" in added
    assert "Old" in deleted
```

### Integration Tests

```python
def test_end_to_end_processing():
    """Test end-to-end event processing"""
    change_event = {
        "entity_id": "Q42",
        "from_revision_id": 100,
        "to_revision_id": 101
    }
    
    # Process event
    process_entity_change(change_event)
    
    # Verify event was emitted
    assert kafka_consumer.poll(timeout=5) is not None
```

## Deployment

### Container Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose metrics endpoint
EXPOSE 9090

# Run application
CMD ["python", "rdf_change_streamer.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rdf-change-streamer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rdf-change-streamer
  template:
    metadata:
      labels:
        app: rdf-change-streamer
    spec:
      containers:
      - name: streamer
        image: rdf-change-streamer:latest
        env:
        - name: KAFKA_BROKERS
          value: "kafka:9092"
        - name: INPUT_TOPIC
          value: "wikibase.entity_change"
        - name: OUTPUT_TOPIC
          value: "wikibase.rdf_change"
        - name: S3_BUCKET
          value: "wikibase-revisions"
        ports:
        - containerPort: 9090
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

## References

- [MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md](MEDIAWIKI-INDEPENDENT-CHANGE-DETECTION.md) - Change detection service documentation
- [RDF-DIFF-STRATEGY.md](RDF-DIFF-STRATEGY.md) - RDF diff strategy (Option A: Full Convert + Diff)
- [CHANGE-DETECTION-RDF-GENERATION.md](CHANGE-DETECTION-RDF-GENERATION.md) - Complete RDF generation architecture
- [SCHEMAS-EVENT-PRIMARY-SUMMARY.md](../SCHEMAS-EVENT-PRIMARY-SUMMARY.md) - RDF change schema documentation
- [STREAMING-UPDATER-CONSUMER.md](../STREAMING-UPDATER-CONSUMER.md) - Existing RDF consumer for Blazegraph
