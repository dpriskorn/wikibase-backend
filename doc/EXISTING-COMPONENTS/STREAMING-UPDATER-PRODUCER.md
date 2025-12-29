# Streaming Updater Producer

Apache Flink-based Kafka producer that processes MediaWiki events and generates RDF mutation events for the Wikidata Query Service.

## Overview

The Streaming Updater Producer is a fault-tolerant streaming application that:
- Consumes MediaWiki events from Kafka (revision-create, page-delete, page-undelete, etc.)
- Fetches entity data from MediaWiki via HTTP
- Computes RDF diffs between entity revisions
- Emits mutation events to Kafka for consumption by the Streaming Updater Consumer
- Supports exactly-once semantics with checkpointing and savepoints

## Architecture

**Data Flow:**
```
MediaWiki Events (Kafka)
         ↓
    Event Filtering (by domain, namespace, content model)
         ↓
    Fetch Entity Data (MediaWiki API)
         ↓
    Generate RDF Diff (compare revisions)
         ↓
    Reorder & Deduplicate (event windowing)
         ↓
    Mutation Events → Kafka (output topics)
         ↓
    Side Outputs (reconciliation, errors) → Kafka
```

## Core Components

### Main Pipeline (UpdaterJob.scala)
- **Incoming Streams**: Consumes MediaWiki events from Kafka or Event Platform API
- **Wikibase Repository**: Fetches entity data from MediaWiki via HTTP
- **Subgraph Assigner**: Splits entity data into subgraphs for distributed processing
- **Reorder Operator**: Handles out-of-order events with configurable windowing
- **Mutation Resolver**: Determines which mutations to apply
- **Output Streams**: Emits mutation events to Kafka with exactly-once guarantees

### Bootstrap Job (UpdaterBootstrapJob.scala)
- Initializes pipeline state from a historical entity→revision mapping
- Creates savepoints for fast deployment
- Used for initial data load and recovery scenarios

### State Extraction Job (StateExtractionJob.scala)
- Extracts and validates Flink savepoint state
- Used for debugging and state migration

## Technology Stack

- **Apache Flink 1.17.1** - Stream processing engine with exactly-once guarantees
- **Apache Kafka 3.2.3** - Event streaming platform
- **Scala 2.12.13** - Pipeline implementation language
- **Java** - Utility classes and serializers
- **RocksDB** - State backend for large state
- **MediaWiki API** - Entity data source

## Key Features

### Event Processing
- **Multi-topic consumption**: Reads from revision-create, page-delete, page-undelete, and page-suppress topics
- **Domain filtering**: Processes events only for specified MediaWiki instance (e.g., www.wikidata.org)
- **Namespace filtering**: Handles specific entity namespaces (items, properties, lexemes, mediainfo)
- **Content model filtering**: Filters by Wikibase content models

### Mutation Generation
- **RDF diff computation**: Compares entity revisions to generate RDF triple mutations
- **Async IO fetch**: Concurrent fetching of entity data with retry logic
- **Reordering window**: Configurable window to handle out-of-order events
- **Deduplication**: Removes duplicate events based on revision ID

### State Management
- **Checkpointing**: Periodic checkpoints for fault tolerance (default: 30s)
- **Savepoints**: Manual savepoints for upgrades and recovery
- **RocksDB state backend**: Handles large state efficiently
- **Exactly-once semantics**: Ensures no duplicate or lost mutations

### Output Options
- **Main mutation stream**: Primary output with RDF mutation data
- **Subgraph support**: Splits output into multiple topics for distributed indexing
- **Side outputs**: Reconciliation events and error handling
- **Multiple schema versions**: Supports v1 and v2 mutation schemas

## Configuration

Key configuration options in `updater-job.properties`:

| Option | Description | Default |
|--------|-------------|---------|
| `hostname` | MediaWiki instance to process events for | `www.wikidata.org` |
| `entity_namespaces` | Entity namespaces to process | `0,120,146` |
| `checkpoint_dir` | Flink checkpoint directory | HDFS path |
| `brokers` | Kafka brokers | kafka-jumbo1015.eqiad.wmnet:9092 |
| `output_topic` | Main mutation output topic | wdqs_streaming_updater |
| `parallelism` | Pipeline parallelism | 1 |
| `checkpoint_interval` | Checkpoint interval (ms) | 30000 |
| `reordering_window_length` | Event reordering window (ms) | 60000 |

### Bootstrap Configuration

`bootstrap-config.properties`:
- `revisions_file`: CSV file with entity→revision mapping (from Spark job)
- `savepoint_dir`: Output directory for generated savepoint
- `parallelism`: Bootstrap job parallelism

## Deployment

### Building the Application

```bash
cd wikidata-query-rdf/streaming-updater-producer
mvn package
```

This creates a fat jar: `streaming-updater-producer-{version}-jar-with-dependencies.jar`

### Running the Main Updater

```bash
flink run \
  --class org.wikidata.query.rdf.updater.UpdaterJob \
  -p 1 \
  --detached \
  /path/to/streaming-updater-producer-{version}-jar-with-dependencies.jar \
  /path/to/updater-job.properties
```

### Running the Bootstrap Job

```bash
flink run \
  --class org.wikidata.query.rdf.updater.UpdaterBootstrapJob \
  --detached \
  /path/to/streaming-updater-producer-{version}-jar-with-dependencies.jar \
  /path/to/bootstrap-config.properties
```

### Managing Savepoints

```bash
# Create savepoint
flink savepoint <job-id> /path/to/savepoint

# Restore from savepoint
flink run -s /path/to/savepoint ...
```

## Monitoring

**Metrics exposed via Flink:**
- Kafka consumer lag per topic
- HTTP request success/failure rates
- Mutation event counts
- Checkpoint durations and success rates
- Backpressure indicators

**JMX Metrics:**
- HTTP client retry counts
- Entity fetch latency distributions
- RDF diff generation times

## Testing

```bash
# Run unit tests
mvn test

# Run integration tests
mvn verify
```

## Dependencies

Main dependencies (from pom.xml):
- `org.apache.flink:*` - Flink core and streaming
- `org.apache.kafka:*` - Kafka clients
- `org.wikidata.query.rdf:streaming-updater-common` - Shared models
- `org.wikidata.query.rdf:tools` - Wikibase repository client
- `org.wikimedia:eventutilities-flink` - Event Platform integration

## License

Apache License 2.0
