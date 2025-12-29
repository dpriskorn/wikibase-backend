# Streaming Updater Consumer

Kafka consumer that reads mutation events from the Streaming Updater Producer and applies RDF patches to the Blazegraph triple store in real-time.

## Overview

The Streaming Updater Consumer is a lightweight Java application that:
- Consumes RDF mutation events from Kafka (produced by Streaming Updater Producer)
- Accumulates and deduplicates mutations for each entity
- Applies RDF patches to Blazegraph via HTTP
- Monitors update consistency and emits metrics
- Supports manual offset management and recovery

## Architecture

**Data Flow:**
```
Mutation Events (Kafka)
         ↓
    KafkaStreamConsumer (batching, buffering)
         ↓
    PatchAccumulator (accumulate per-entity mutations)
         ↓
    RDFPatchBuilder (build RDF patch)
         ↓
    RdfRepositoryUpdater (apply patch via HTTP)
         ↓
    Blazegraph Triple Store
```

## Core Components

### StreamingUpdate.java (Main Entry Point)
- Parses command-line options and initializes the consumer
- Configures Kafka consumer with retry logic
- Sets up HTTP client for Blazegraph communication
- Initializes JMX metrics reporting
- Registers shutdown hooks for graceful exit

### StreamingUpdaterConsumer.java (Consumer Logic)
- Polls Kafka for mutation events in batches
- Accumulates mutations into RDF patches
- Applies patches to Blazegraph via HTTP
- Tracks and reports metrics (mutations, divergences, latencies)
- Monitors inconsistency thresholds
- Commits Kafka offsets after successful patch application

### KafkaStreamConsumer.java
- Manages Kafka consumer lifecycle
- Handles batching and buffering of messages
- Supports initial offset configuration (earliest, specific offset, or timestamp)
- Filters events by entity ID pattern
- Emits metrics for consumer lag and throughput

### PatchAccumulator.java
- Accumulates mutations per entity
- Deduplicates redundant mutations
- Removes old mutations when newer ones arrive
- Builds final RDF patch from accumulated mutations

### MutationEventDataJsonKafkaDeserializer.java
- Deserializes mutation events from JSON
- Supports multiple schema versions (V1, V2)
- Validates event structure

## Technology Stack

- **Java** - Application language
- **Apache Kafka 3.2.3** - Event streaming
- **Eclipse Jetty** - HTTP client for Blazegraph communication
- **OpenRDF Sesame** - RDF model and serialization
- **Dropwizard Metrics** - Metrics and monitoring
- **Guava** - Retry logic and utilities
- **Lombok** - Code generation

## Key Features

### Kafka Integration
- **Manual partition assignment**: Reads from specific partition
- **Consumer group**: For offset tracking and monitoring
- **Initial offset control**: Start from earliest, specific offset, or timestamp
- **Entity filtering**: Filter events by entity ID pattern (regex)
- **Canary event filtering**: Skips test/canary events

### Patch Application
- **Batch processing**: Accumulates multiple mutations into a single patch
- **Buffered input**: Configurable message buffer for batching
- **Deduplication**: Removes redundant mutations automatically
- **HTTP retry**: Automatic retry logic for failed requests
- **Timeout handling**: Configurable timeouts for HTTP requests

### Metrics & Monitoring
**JMX Metrics:**
- `mutations` - Total mutations applied
- `divergences` - Difference between expected and actual mutations
- `shared-element-mutations` - Shared element mutations
- `delete-mutations` - Deletion mutations
- `reconciliation-mutations` - Reconciliation mutations
- `poll-time-cnt` - Kafka poll latency
- `rdf-store-time-cnt` - Blazegraph update latency

### Consistency Checking
- **Inconsistency threshold**: Warns when actual mutations differ significantly from expected
- **Divergence tracking**: Monitors mutations that couldn't be applied
- **Reconciliation mutation tracking**: Tracks mutations applied for consistency

## Configuration

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--brokers` | Kafka broker addresses | `kafka-jumbo1001.eqiad.wmnet:9092` |
| `--topic` | Kafka input topic | `wdqs_streaming_updater` |
| `--partition` | Kafka partition to consume | `0` |
| `--consumer_group` | Consumer group ID | `wdqs_streaming_updater_consumer` |
| `--batch_size` | Max batch size | `10` |
| `--buffered_input_messages` | Buffer size for batching | `1000` |
| `--initial_offsets` | Initial offset (earliest/number/timestamp) | `earliest` or `12345` or `2024-01-01T00:00:00Z` |
| `--sparql_uri` | Blazegraph update endpoint | `http://localhost:9999/bigdata/namespace/wdq/sparql` |
| `--inconsistencies_warning_threshold` | Warning threshold for inconsistencies | `0.05` (5%) |
| `--entity_filter_pattern` | Regex to filter entities | `Q\\d+` |
| `--metric_domain` | JMX metrics domain | `org.wikidata.query.rdf.updater.consumer` |

### Example Commands

```bash
# Start consumer from earliest offset
java -jar streaming-updater-consumer.jar \
  --brokers kafka-jumbo1001.eqiad.wmnet:9092 \
  --topic wdqs_streaming_updater \
  --partition 0 \
  --consumer_group wdqs_consumer \
  --sparql_uri http://localhost:9999/bigdata/namespace/wdq/sparql \
  --initial_offsets earliest

# Start from specific timestamp
java -jar streaming-updater-consumer.jar \
  --brokers kafka-jumbo1001.eqiad.wmnet:9092 \
  --topic wdqs_streaming_updater \
  --partition 0 \
  --consumer_group wdqs_consumer \
  --sparql_uri http://localhost:9999/bigdata/namespace/wdq/sparql \
  --initial_offsets 2024-01-01T00:00:00Z

# Start from specific offset
java -jar streaming-updater-consumer.jar \
  --brokers kafka-jumbo1001.eqiad.wmnet:9092 \
  --topic wdqs_streaming_updater \
  --partition 0 \
  --consumer_group wdqs_consumer \
  --sparql_uri http://localhost:9999/bigdata/namespace/wdq/sparql \
  --initial_offsets 123456
```

## Building and Deployment

### Build Application

```bash
cd wikidata-query-rdf/streaming-updater-consumer
mvn package
```

This creates: `streaming-updater-consumer-{version}-jar-with-dependencies.jar`

### Run Locally

```bash
java -jar target/streaming-updater-consumer-{version}-jar-with-dependencies.jar \
  --brokers localhost:9092 \
  --topic wdqs_streaming_updater \
  --partition 0 \
  --consumer_group wdqs_consumer \
  --sparql_uri http://localhost:9999/bigdata/namespace/wdq/sparql \
  --initial_offsets earliest
```

### Monitoring with JConsole

```bash
jconsole <pid>
```

Look for metrics under: `org.wikidata.query.rdf.updater.consumer`

## Error Handling

### HTTP Errors
- Automatic retry with exponential backoff
- Configurable timeout (default: 3s poll timeout)
- Metrics track retry counts

### Kafka Errors
- Consumer polls with timeout to detect failures
- Offsets committed only after successful patch application
- Manual offset control for recovery

### Consistency Warnings
- Warnings logged when inconsistency threshold exceeded
- Divergence counter tracks missed mutations
- Threshold configurable via `--inconsistencies_warning_threshold`

## Dependencies

Main dependencies (from pom.xml):
- `org.apache.kafka:kafka-clients` - Kafka consumer
- `org.eclipse.jetty:jetty-client` - HTTP client
- `io.dropwizard.metrics:metrics-core` - Metrics
- `org.openrdf.sesame:*` - RDF model
- `com.google.guava:guava` - Utilities
- `com.github.rholder:guava-retrying` - Retry logic
- `org.wikidata.query.rdf:streaming-updater-common` - Shared models
- `org.wikidata.query.rdf:tools` - RDF repository updater

## Testing

```bash
# Run unit tests
mvn test
```

Test files:
- `StreamingUpdaterConsumerUnitTest.java`
- `KafkaStreamConsumerUnitTest.java`
- `MutationEventDataJsonKafkaDeserializerUnitTest.java`
- `UpdatePatchAccumulatorUnitTest.java`

## Recovery Procedures

### Reset to Specific Offset

```bash
java -jar streaming-updater-consumer.jar \
  --initial_offsets <offset_number> \
  ...
```

### Reset to Timestamp

```bash
java -jar streaming-updater-consumer.jar \
  --initial_offsets 2024-01-01T00:00:00Z \
  ...
```

### Re-process from Earliest

```bash
java -jar streaming-updater-consumer.jar \
  --initial_offsets earliest \
  ...
```

## License

Apache License 2.0
