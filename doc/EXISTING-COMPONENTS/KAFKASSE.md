# KafkaSSE

Kafka Consumer to HTTP Server-Sent Events (SSE) bridge library for Node.js.

## Overview

KafkaSSE creates a bridge between Kafka topics and HTTP clients using the SSE/EventSource protocol. It consumes messages from Kafka and streams them to connected web clients in real-time, with automatic reconnection support.

**Version:** 0.4.3  
**Purpose:** Stream Kafka messages to web clients via HTTP SSE

## Core Architecture

### KafkaSSE Class (`lib/KafkaSSE.js`)
Main consumer class that manages Kafka connections and SSE streaming:

- **Connects to Kafka**: Creates node-rdkafka KafkaConsumer instance
- **Consumes messages**: Uses standard non-flowing consume API
- **Sends to clients**: Formats and sends messages as SSE events
- **Tracks offsets**: Maintains latest offsets for each topic-partition
- **Handles reconnections**: Uses `Last-Event-ID` header for resume capability

### SSEResponse Class (`lib/SSEResponse.js`)
HTTP response wrapper for SSE formatting:

- **Starts SSE stream**: Writes HTTP 200 headers with `text/event-stream` content-type
- **Formats events**: Applies SSE protocol formatting (event, data, id fields)
- **Supports JSON**: Optional raw JSON mode (newline-delimited) for `Accept: application/json`
- **Manages backpressure**: Handles response drain events properly

### Utility Functions (`lib/utils.js`)
Helper functions for Kafka and message operations:

- **createKafkaConsumerAsync**: Promisified KafkaConsumer creation
- **validateAssignments**: Validates topic assignment format
- **buildAssignmentsAsync**: Converts topic names to partition assignments
- **assignmentsForTimesAsync**: Resolves timestamps to Kafka offsets
- **deserializeKafkaMessage**: Parses JSON and adds metadata

### Error Classes (`lib/error.js`)
Custom error hierarchy:

- **ExtendableError**: Base class with proper error serialization
- **KafkaSSEError**: Extends ExtendableError with `origin: 'KafkaSSE'`
- **ConfigurationError**: Invalid KafkaSSE configuration
- **InvalidAssignmentError**: Malformed assignment array
- **TopicNotAvailableError**: Requested topic doesn't exist
- **DeserializationError**: Message deserialization failure
- **FilterError**: Filter function error

## Key Features

### Automatic Reconnection
Clients using EventSource automatically reconnect and resume:

1. Each SSE event includes `id` field with latest offset information
2. On reconnection, EventSource sends `Last-Event-ID` header
3. KafkaSSE uses header to resume from exact position

**Last-Event-ID format:**
```json
[
  {topic: "topicA", partition: 0, offset: 12345},
  {topic: "topicB", partition: 0, timestamp: 1527858324658}
]
```

### Timestamp-Based Offsets
Support for timestamp-based consumption for multi-datacenter deployments:

- **useTimestampForId option**: Uses timestamps instead of offsets in event IDs
- **Offset resolution**: Kafka queried for offset at given timestamp
- **Multi-DC support**: Offsets don't match across different Kafka clusters
- **Fallback**: Offsets take precedence over timestamps in `Last-Event-ID`

**Use case:** Historical playback without knowing logical offsets
```
/v2/stream/edits?since=1527858324658
```

### Custom Deserialization
Override default JSON deserialization for custom message formats:

```javascript
function customDeserializer(kafkaMessage) {
    kafkaMessage.message = JSON.parse(kafkaMessage.value.toString());
    kafkaMessage.message.meta = {
        timestamp: kafkaMessage.timestamp,
        customField: 'custom value'
    };
    return kafkaMessage;
}
```

**Requirements:**
- Must set `kafkaMessage.message` property
- Must preserve `topic`, `partition`, `offset` fields
- These fields used for `Last-Event-ID` generation

### Server-Side Filtering
Filter messages before sending to clients:

```javascript
function priceFilter(kafkaMessage) {
    return kafkaMessage.message.price >= 10.0;
}
```

**Use cases:**
- Remove sensitive data
- Filter by event type
- Rate limiting per client
- Client-specific routing

### Consumer State Management
Intentional design to avoid Kafka state changes from internet:

- **No offset commits**: Commits disabled entirely
- **Unique consumer groups**: Each client gets unique group ID
- **No rebalancing**: Uses `assign()` instead of `subscribe()`
- **Client-managed state**: Offset tracking pushed to clients

**Rationale:**
- Public internet cannot be trusted with Kafka mutations
- Supports infinite scaling (each client = independent consumer)
- Simplifies architecture (no consumer group coordination)

## API Usage

### Main Export Function

```javascript
const kafkaSse = require('kafka-sse');

kafkaSse(req, res, assignments, options, atTimestamp);
```

**Parameters:**
- `req`: HTTP ClientRequest object
- `res`: HTTP ServerResponse object
- `assignments`: Array of topic names or assignment objects
- `options`: Configuration object (see below)
- `atTimestamp`: Optional Unix epoch milliseconds for historical playback

### Configuration Options

| Option | Type | Default | Description |
|--------|------|----------|-------------|
| `kafkaConfig` | Object | node-rdkafka KafkaConsumer config (broker list, etc.) |
| `allowedTopics` | Array | Whitelist of topics allowed for consumption |
| `logger` | Bunyan | Bunyan logger instance (creates new if not provided) |
| `disableSSEFormatting` | Boolean | Send raw JSON instead of SSE format |
| `deserializer` | Function | Custom message deserialization function |
| `filterer` | Function | Message filter function |
| `useTimestampForId` | Boolean | Use timestamps instead of offsets for Last-Event-ID |
| `kafkaEventHandlers` | Object | node-rdkafka event name → handler function |
| `connectErrorHandler` | Function | Custom error handler for initialization errors |
| `idleDelayMs` | Integer | Delay in ms between empty consume cycles (default: 100) |

### Kafka Configuration
Merged with defaults and mandatory settings:

**Defaults:**
```javascript
{
    'metadata.broker.list': 'localhost:9092',
    'client.id': `KafkaSSE-${uuid}`
}
```

**Mandatory (overridden):**
```javascript
{
    'enable.auto.commit': false,
    'group.id': `KafkaSSE-${uuid}`
}
```

**Optional:**
- `default_topic_config`: Topic-specific configuration (e.g., `auto.offset.reset`)

## Event Processing Flow

```
HTTP Request arrives
         ↓
Parse Last-Event-ID header (if present)
         ↓
Validate assignments format
         ↓
Create KafkaConsumer with unique group ID
         ↓
Query Kafka metadata for available topics
         ↓
Validate requested topics exist
         ↓
Build partition assignments:
  - From Last-Event-ID (preferred)
  - From atTimestamp (fallback)
  - From -1/latest (default)
         ↓
Resolve timestamps to offsets (if needed)
         ↓
Assign consumer to topic-partitions
         ↓
Write HTTP 200 with SSE headers
         ↓
Begin consume loop
         ↓
For each message:
  1. Consume from Kafka
  2. Deserialize message
  3. Apply filter (if configured)
  4. Update latest offsets map (+1 to avoid re-consumption)
  5. Format as SSE event
  6. Write to response
  7. Loop
         ↓
On client disconnect:
  - Disconnect KafkaConsumer
  - End HTTP response
  - Cleanup listeners
```

## Client Usage

### Browser EventSource
```javascript
const eventSource = new EventSource('http://host:6927/topic1,topic2');

eventSource.onopen = () => {
    console.log('SSE connection opened');
};

eventSource.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log(message);
};

eventSource.onerror = (event) => {
    console.error('SSE error:', event);
};
```

### Node.js EventSource
```javascript
const EventSource = require('eventsource');
const eventSource = new EventSource('http://localhost:6927/topics');

eventSource.addEventListener('message', (event) => {
    console.log(JSON.parse(event.data));
});
```

### Historical Consumption
Using `since` query parameter:
```javascript
const oneHourAgo = Date.now() - (60 * 60 * 1000);
const url = `http://host:6927/edits?since=${oneHourAgo}`;
const eventSource = new EventSource(url);
```

## Assignment Formats

### Topic Names (Array)
Consume from all partitions starting at latest or timestamp:
```javascript
['topic1', 'topic2']
// or
['topic1,topic2']
```

### Topic Names (String)
Comma-delimited topic names:
```javascript
'topic1,topic2'
```

### Assignment Objects (Array)
Precise control over topic, partition, offset/timestamp:
```javascript
[
    {topic: 'topic1', partition: 0, offset: 12345},
    {topic: 'topic2', partition: 0, timestamp: 1527858324658},
    {topic: 'topic3', partition: 0}  // Starts at latest/timestamp
]
```

**Offset vs Timestamp:**
- **offset**: Exact position in partition
- **timestamp**: Kafka queried for offset at this time
- **Both specified**: Offset takes precedence

## SSE Event Format

### Standard SSE
```
data: {"event":"data"}
id: {"topic":"topicA","partition":0,"offset":12345}

data: {"event":"data2"}
id: {"topic":"topicA","partition":0,"offset":12346}

data: {"event":"data3"}
id: {"topic":"topicA","partition":0,"offset":12347}
```

### JSON Mode (Accept: application/json)
```json
{"event":"data","meta":{"topic":"topicA","partition":0,"offset":12345}}
{"event":"data2","meta":{"topic":"topicA","partition":0,"offset":12346}}
```

## HTTP Response Headers

### SSE Mode
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### JSON Mode
```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
```

## Error Handling

### Initialization Errors
Errors before SSE stream starts result in HTTP error responses:

| Error Type | Status | When |
|------------|--------|-------|
| InvalidAssignmentError | 400 | Malformed assignments or Last-Event-ID |
| TopicNotAvailableError | 404 | Topic doesn't exist |
| ConfigurationError | 500 | Invalid configuration |

**Response:**
```json
{
    "name": "InvalidAssignmentError",
    "message": "Must provide either an array topic names...",
    "origin": "KafkaSSE",
    "assignments": [...]
}
```

### Runtime Errors
Errors after SSE stream starts sent as SSE error events:

```
event: error
data: {"name": "...", "message": "..."}
id: {"topic":"...","partition":0,"offset":123}
```

**Client handling:**
```javascript
eventSource.onerror = (event) => {
    console.error('SSE error:', event);
    // EventSource will auto-reconnect
};
```

### Kafka Errors
Ignored innocuous errors, real errors terminate stream:

| Error Code | Action |
|------------|--------|
| ERR__PARTITION_EOF | Log trace, delay 100ms, continue |
| ERR__TIMED_OUT | Log trace, delay 100ms, continue |
| Other | Log error, throw to client |

## Development & Testing

### Running Tests
```bash
# Full Jenkins test (downloads Kafka, runs tests, cleans up)
npm test

# Local Kafka (requires running Kafka at localhost:9092)
npm run test-local

# Docker-based testing
npm run test-docker
```

### Coverage
```bash
npm run coverage
```

### Manual Kafka Setup
```bash
# Download and install Kafka
npm run kafka-install

# Start Kafka
npm run kafka-start

# Stop Kafka
npm run kafka-stop

# Load test fixtures
npm run kafka-fixture
```

### Test Structure
- `test/KafkaSSE.js`: KafkaSSE class tests
- `test/SSEResponse.js`: SSE response formatting tests
- `test/utils.js`: Utility function tests
- `test/docker/`: Docker-based integration tests
- `test/utils/kafka_fixture.sh`: Kafka topic and message setup

## Security Considerations

1. **No Offset Commits**: Prevents untrusted clients from altering Kafka state
2. **Unique Consumer Groups**: Each client isolated, no shared state
3. **Topic Whitelisting**: `allowedTopics` restricts consumption
4. **Allowed Topics Enforcement**: `allowedTopics` in assignments prevents unauthorized topic access
5. **No Consumer Group Balancing**: Uses `assign()` to avoid rebalance attacks
6. **X-Request-ID**: Uses client-provided ID or generates UUID for tracing

## Memory Management

### Known Issue: node-rdkafka Event Leak
node-rdkafka event emitters can leak memory if enabled.

**Workaround:**
```javascript
// KafkaSSE disables event_cb by default unless kafkaEventHandlers is set
if (!this.options.kafkaEventHandlers) {
    defaultKafkaConfig.event_cb = false;
}
```

**Recommendation:** Avoid setting `kafkaEventHandlers` unless necessary.

## Dependencies

### Core
- `node-rdkafka`: Kafka consumer client (v2.3.4)
- `bluebird`: Promise library (v3.5.1)
- `lodash`: Utility functions (v4.15.0)
- `bunyan`: Structured logging (v1.8.1)
- `uuid`: UUID generation (v3.3.2)
- `safe-regex`: Safe regular expression creation (v1.1.0)

### Dev Dependencies
- `mocha`: Test framework (v2.5.3)
- `istanbul`: Code coverage (v0.4.4)
- `eventsource`: Node.js EventSource polyfill (v0.2.1)
- `sinon`: Test doubles (v1.17.6)
- `node-fetch`: HTTP requests for tests (v1.6.3)

## File Structure

```
KafkaSSE/
├── lib/
│   ├── KafkaSSE.js              # Main KafkaSSE consumer class
│   ├── SSEResponse.js          # HTTP SSE response formatter
│   ├── error.js                 # Custom error classes
│   └── utils.js                 # Utility functions
├── test/
│   ├── KafkaSSE.js              # KafkaSSE tests
│   ├── SSEResponse.js          # SSE response tests
│   ├── error.js                 # Error tests
│   ├── utils.js                 # Utility tests
│   ├── utils/
│   │   ├── kafka.sh             # Kafka lifecycle scripts
│   │   ├── kafka_install.sh      # Kafka installation
│   │   └── kafka_fixture.sh      # Test data setup
│   └── docker/
│       ├── docker-compose.yml      # Docker test environment
│       └── kafka/                # Kafka Dockerfile and scripts
├── index.js                    # Main export function
├── client.js                    # Example EventSource client
├── server.js                    # Example HTTP server
├── package.json                 # Dependencies and scripts
└── README.md                    # Documentation
```

## Use Cases

### Real-Time Dashboards
Stream live metrics and events to web browsers:
```javascript
kafkaSse(req, res, ['metrics', 'errors'], {
    kafkaConfig: { 'metadata.broker.list': 'kafka:9092' }
});
```

### Historical Replay
Replay events from specific time period:
```javascript
const oneDayAgo = Date.now() - (24 * 60 * 60 * 1000);
kafkaSse(req, res, ['audit-log'], {
    kafkaConfig: { 'metadata.broker.list': 'kafka:9092' }
}, oneDayAgo);
```

### Multi-Topic Aggregation
Stream from multiple related topics:
```javascript
kafkaSse(req, res, ['page-create', 'page-delete', 'revision-create'], {
    filterer: (msg) => msg.message.domain === 'en.wikipedia.org'
});
```

### Custom Message Transformation
Add metadata or transform message format:
```javascript
kafkaSse(req, res, ['events'], {
    deserializer: (kafkaMessage) => {
        kafkaMessage.message = JSON.parse(kafkaMessage.value);
        kafkaMessage.message.kafkaMeta = {
            topic: kafkaMessage.topic,
            timestamp: kafkaMessage.timestamp
        };
        return kafkaMessage;
    }
});
```

## Related Services

- **EventStreams**: Wikimedia event streaming service (uses KafkaSSE)
- **EventGate**: Wikimedia event ingestion service (produces to Kafka)
- **node-rdkafka**: Kafka client library
- **Kasocki**: SockJS-based Kafka to WebSocket bridge

## References

- [README.md](KafkaSSE/README.md) - Full usage documentation
- [package.json](KafkaSSE/package.json) - Dependencies and scripts
- [client.js](KafkaSSE/client.js) - Example EventSource client
- [server.js](KafkaSSE/server.js) - Example HTTP server
- [node-rdkafka](https://github.com/Blizzard/node-rdkafka) - Kafka client library
- [W3C EventSource](https://www.w3.org/TR/eventsource/) - SSE specification
