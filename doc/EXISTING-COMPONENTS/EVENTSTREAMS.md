# EventStreams

Public service that streams MediaWiki and Wikimedia events over HTTP using Server-Sent Events (SSE) backed by Kafka.

## Overview

EventStreams exposes Kafka event streams to clients via HTTP SSE or newline-delimited JSON. It acts as a gateway between Kafka topics and web clients, consuming from multiple Kafka topics and streaming events in real-time.

**Version:** 0.19.0-dev  
**Purpose:** Real-time event streaming for Wikimedia infrastructure

## Core Architecture

### Streaming Engine
Built on top of **@wikimedia/kafka-sse** (KafkaSSE), which:
- Consumes from Kafka topics
- Emits events as SSE or JSON to connected clients
- Handles automatic reconnection via `Last-Event-ID` header
- Supports timestamp-based offset lookup for multi-datacenter scenarios

### Route Configuration
Stream definitions are loaded from external configuration (`stream_config_uri`), enabling:
- Dynamic stream discovery and routing
- Stream aliases for simplified access
- Per-stream topic configuration
- Schema-based documentation generation

## Routes

### Main Endpoints

**GET /v2/stream/{streams}**
- Subscribe to one or more comma-separated stream names
- Returns never-ending SSE stream (default) or newline-delimited JSON
- Parameters:
  - `streams` (path): Comma-separated list of stream names
  - `since` (query): Unix timestamp or date string for historical playback
- Headers:
  - `Last-Event-ID`: Array of `{topic, partition, timestamp}` for resume capability
  - `Accept`: `application/json` for JSON, `text/event-stream` for SSE (default)

**GET /v2/ui** (optional)
- Interactive web UI for exploring streams
- Requires `stream_ui_enabled` configuration and built UI (`npm run build-ui`)

**GET /?spec=true**
- Returns OpenAPI specification with dynamic stream routes

**GET /?doc=true**
- Returns Swagger UI documentation

### Info Endpoints

**GET /_info/**
- `GET /_info/` - Service name, version, description, homepage
- `GET /_info/name` - Service name
- `GET /_info/version` - Service version
- `GET /_info/home` - Redirect to homepage

### Legacy Routes

**GET /rc**
- Deprecated RCStream service endpoint
- Redirects to `/`?doc`

## Key Features

### Stream Configuration
Dynamic stream definitions from external config:

```yaml
mediawiki.page-create:
  topics: [eqiad.mediawiki.page-create, codfw.mediawiki.page-create]
  stream_aliases: [page-create]
  description: Page create events
  schema_title: mediawiki/revision/create
```

### Multi-Stream Subscription
Single request to multiple streams:
```
/v2/stream/edits,page-create,revision-create
```

### Historical Playback
Resume consumption from historical timestamps:
- `since` query parameter: Unix epoch or date string
- `Last-Event-ID` header: Per-topic-partition offset assignments
- Uses timestamps instead of offsets for multi-datacenter support

### Content Formats
**SSE (default) - text/event-stream:**
```
data: {"event":"data"}
id: {"topic":"topic","partition":0,"timestamp":1234567890}

```

**JSON (Accept: application/json):**
```json
{"event":"data","meta":{"topic":"topic","partition":0,"offset":123}}
```

### Automatic Reconnection
EventSource clients automatically reconnect using `Last-Event-ID`:
- Stores topic, partition, and timestamp from last received event
- Resumes from exact position on reconnection
- No manual offset management required

### Page Redaction
Configurable redaction of sensitive user information:
- `mediawiki_redacted_pages`: Map of wiki to pages requiring redaction
- Removes actor/performer/user fields for specified pages
- Normalizes page titles (lowercase, underscores) for matching
- Logs redaction events with client context

Supported stream types:
- `mediawiki.page_change.v1`: Removes `performer` and `revision.editor`
- `mediawiki.recentchange`: Removes `user`
- Other streams: Removes `performer` based on `page_title`

### Rate Limiting
Per-IP concurrent connection limits:
- `client_ip_connection_limit`: Maximum concurrent connections per IP
- Requires `X-Client-IP` header
- Returns HTTP 429 when limit exceeded

### Metrics
Built-in Prometheus metrics:
- `eventstreams_connected_clients`: Gauge of current clients per stream
- `eventstreams_client_connections_total`: Counter of total connections per stream combination
- Kafka consumer metrics (filtered via `rdkafkaStatsFilter`)

## Configuration

### Stream Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `stream_config_uri` | required | URI to load stream configurations from |
| `stream_config_object_path` | undefined | Dotted path to stream config in fetched object |
| `stream_config_ttl` | undefined | Refresh interval in seconds (0 = no refresh) |
| `stream_config_defaults` | undefined | Default values applied to all streams |
| `stream_config_overrides` | undefined | Per-stream configuration overrides |
| `allowed_streams` | undefined | Filter streams to only these names |
| `stream_ui_enabled` | false | Enable HTML UI at `/v2/ui` |

### Kafka Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `kafka.conf` | required | node-rdkafka consumer configuration |
| `kafka.group_id` | required | Kafka consumer group ID |
| `kafka.consumer.request.timeout.ms` | 30000 | Consumer request timeout |

### Schema Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `schema_base_uris` | undefined | Base URIs for resolving schema URLs |
| `schema_latest_version` | undefined | Latest version for schema URI construction |
| `schema_title` | undefined | Schema title for documentation |
| `$schema` | undefined | Explicit schema URI for stream |

### Security Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `client_ip_connection_limit` | undefined | Max concurrent connections per IP |
| `mediawiki_redacted_pages` | undefined | Map of wiki to redacted pages |

### Service Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `port` | 8888 | HTTP listener port |
| `interface` | `0.0.0.0` | HTTP listener interface |
| `user_agent` | `eventstreams` | User-Agent for HTTP requests |
| `cors` | `*` | CORS allowed origins |
| `csp` | strict | Content Security Policy |

## Event Processing Flow

```
Client Request GET /v2/stream/edits?page-create
         ↓
Load and validate stream configs
         ↓
Validate requested stream names
         ↓
Collect topics from all requested streams
         ↓
Apply allowed_topics restrictions
         ↓
Enforce connection limits (if configured)
         ↓
Initialize Kafka consumer
         ↓
Determine starting offset:
  - Last-Event-ID header (preferred)
  - since query parameter
  - Latest offset (default)
         ↓
Begin consuming from Kafka topics
         ↓
For each message:
  - Deserialize message
  - Add Kafka metadata (topic, partition, offset)
  - Apply page redaction (if configured)
  - Format as SSE or JSON
  - Send to client
         ↓
Client disconnects:
  - Track metrics
  - Decrement connection count
```

## Message Format

### SSE Event
```
id: {"topic":"eqiad.mediawiki.revision-create","partition":0,"offset":12345}
data: {"meta":{"stream":"mediawiki.revision-create"},"event":"..."}
```

### JSON Event
```json
{
  "message": {
    "meta": {
      "stream": "mediawiki.revision-create",
      "topic": "eqiad.mediawiki.revision-create",
      "partition": 0,
      "offset": 12345
    },
    "event": "..."
  }
}
```

### Last-Event-ID Format
```json
[
  {
    "topic": "eqiad.mediawiki.revision-create",
    "partition": 0,
    "timestamp": 1234567890000
  }
]
```

## HTTP Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Successful stream established |
| 303 | Redirect (root to UI or docs) |
| 301 | Permanent redirect (legacy routes) |
| 400 | Invalid request (bad stream, missing header, invalid timestamp) |
| 429 | Too many concurrent connections |
| 500 | Misconfigured stream topics |

## Stream Configuration Details

### Topics Configuration
```yaml
stream-name:
  topics: [eqiad.topic, codfw.topic]
  topics_allowed: [eqiad.topic, codfw.topic]  # Optional whitelist
```

- `topics`: Default/preferred topics for new connections
- `topics_allowed`: Valid topics for this stream (enforces Last-Event-ID limits)

### Stream Aliases
```yaml
mediawiki.revision-create:
  topics: [eqiad.mediawiki.revision-create]
  stream_aliases: [revision-create, edits]
```

Creates `/v2/stream/revision-create` and `/v2/stream/edits` routes pointing to the same stream.

### Schema Documentation
Stream configs can include schema information for OpenAPI documentation:
```yaml
stream-name:
  schema_title: mediawiki/revision/create
  $schema: /mediawiki/revision/create/1.0.0
  description: Events for MediaWiki revision creation
```

## Development & Testing

### Building UI
```bash
npm run build-ui
```

### Running Tests
```bash
npm test
```

### Linting
```bash
npm run lint
```

### Coverage
```bash
npm run coverage
```

### Starting Service
```bash
npm start
```

### Test Structure
- `test/features/`: Feature tests for core components
- `test/lib/`: Utility tests
- `test/utils/`: Test utilities and server helpers

## Dependencies

### Core
- `express`: HTTP server
- `@wikimedia/kafka-sse`: Kafka to SSE streaming
- `@wikimedia/service-utils`: Wikimedia service framework
- `node-rdkafka`: Kafka consumer
- `lodash`: Utility functions
- `winston`: Logging

### UI Dependencies
- Vue.js-based UI in `ui/` directory
- Requires separate `npm install` and `npm run build` in `ui/`

## Security Considerations

1. **Page Redaction**: Configurable redaction of user information for sensitive pages
2. **Connection Limiting**: Per-IP concurrent connection limits
3. **CSP**: Strict Content Security Policy (media, img, style allowed from any origin)
4. **CORS**: Configurable (default `*`)
5. **No Compression**: Disabled for streaming connections to avoid buffering issues
6. **Header Whitelisting**: Logs only whitelisted request headers

## Multi-Datacenter Support

EventStreams supports active-active multi-datacenter deployment:

1. **Timestamp-Based Offsets**: Uses timestamps instead of offsets in `Last-Event-ID`
2. **Topic Failover**: Stream configs include topics from multiple DCs
3. **Flexible Consumption**: Clients can consume from preferred topics initially, then switch via `Last-Event-ID`

Example:
```yaml
edits:
  topics: [eqiad.mediawiki.revision-create, codfw.mediawiki.revision-create]
```

## File Structure

```
eventstreams/
├── lib/
│   ├── eventstreams-util.js       # Redaction, deserialization, metrics filtering
│   ├── util.js                 # General utilities
│   └── swagger-ui.js           # Swagger UI integration
├── routes/
│   ├── stream.js               # Main streaming endpoint
│   ├── info.js                 # Service info endpoints
│   └── root.js                # Root endpoint (redirects)
├── ui/                        # Vue.js web UI
│   ├── src/                   # UI source code
│   ├── public/                # Static assets
│   └── dist/                  # Built UI (generated)
├── test/
│   ├── features/               # Feature tests
│   ├── lib/                   # Utility tests
│   └── utils/                 # Test utilities
├── scripts/                   # Utility scripts
├── app.js                     # Express app initialization
├── server.js                  # Service entry point
├── spec.yaml                  # OpenAPI specification base
├── stream-config.yaml          # Example stream configuration
└── package.json               # Dependencies and scripts
```

## Related Services

- **EventGate**: Event intake and validation service (in this repository)
- **KafkaSSE**: Kafka to Server-Sent Events library
- **mediawiki-extensions-EventBus**: MediaWiki event production

## Use Cases

### Real-Time Monitoring
- Monitor page edits, deletions, and creations
- Track recent changes across Wikimedia wikis
- Build live dashboards and visualizations

### Event Analysis
- Consume historical events via `since` parameter
- Analyze patterns and trends
- Debug production issues

### Integration
- Feed events into external systems
- Build real-time notifications
- Implement custom processing pipelines

## References

- [README.md](eventstreams/README.md) - Detailed usage documentation
- [spec.yaml](eventstreams/spec.yaml) - OpenAPI specification
- [package.json](eventstreams/package.json) - Full dependency list
- [KafkaSSE README](https://github.com/wikimedia/kafkasse) - Streaming library documentation
- [Wikitech EventStreams](https://wikitech.wikimedia.org/wiki/EventStreams) - Operational documentation
