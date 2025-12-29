# EventGate

HTTP JSON event intake service with schema validation and event production.

## Overview

EventGate is a generic service that accepts JSON events via HTTP POST, validates them against JSONSchemas, and produces them to pluggable destinations (typically Kafka). Valid events pass through the gate, invalid ones do not.

**Version:** 1.9.4-dev  
**Purpose:** Event ingestion, validation, and routing for Wikimedia infrastructure

## Core Architecture

### EventGate Class (`lib/eventgate.js`)
Generic event processing engine that uses injected functions for validation and production:

- **validate(event, context)**: Validates event, returns Promise of validated event or throws ValidationError
- **produce(event, context)**: Produces event, returns Promise of result or throws Error
- **process(events, context)**: Processes event arrays, returns grouped results by status
- **mapToErrorEvent(error, event, context)**: Optional function to convert failures to error events

EventStatus types: `success`, `invalid`, `error`

### EventValidator Class (`lib/EventValidator.js`)
JSONSchema validation engine using AJV:

- Extracts schema URI from events (default: `$schema` field)
- Downloads and caches schemas from URIs
- Compiles validators with AJV
- Supports JSONSchema drafts 04 and 07
- Validates all schemas against `json-schema-secure` for DOS prevention

### Default Factory (`lib/factories/default-eventgate.js`)
Provides out-of-the-box EventGate implementation:

- Schema URI-based validation
- Kafka production via `@wikimedia/node-rdkafka-factory`
- File/stdout output support
- Stream name extraction and sanitization

## Routes

### Main Endpoints

**POST /v1/events**
- Accepts JSON array of events (Content-Type: `application/json`, `text/plain`, or `application/reports+json`)
- Validates each event against its schema
- Produces valid events to configured destinations
- Returns HTTP status based on batch results

**GET /v1/_test/events** (optional)
- Produces configured test events for readiness probes
- Requires `test_events` configuration

**GET /?spec=true**
- Returns OpenAPI specification

**GET /?doc=true**
- Returns Swagger UI documentation

### Info Endpoints

**GET /_info/**
- `GET /_info/` - Service name, version, description, homepage
- `GET /_info/name` - Service name
- `GET /_info/version` - Service version
- `GET /_info/home` - Redirect to homepage

## Key Features

### Schema-Based Validation
- Schema URIs extracted from event fields (configurable via `schema_uri_field`)
- Multiple base URIs supported (`schema_base_uris`) for fallback schema repositories
- Automatic file extension appending (`schema_file_extension`)
- Schema caching to minimize network requests
- Support for both local (`file://`) and remote (`http://`) schemas

### Security
- All schemas validated against AJV's `json-schema-secure` meta schema
- Prevents DOS attacks through unbounded pattern matching/format validation
- Configurable via `allowInsecureSchemas` (not recommended)

### Stream/Topic Routing
- Events routed to Kafka topics based on:
  - Explicit `stream_field` value (recommended)
  - Sanitized schema URI (fallback, replaces non-alphanumeric characters with `_`)
- Supports dotted path notation for nested fields

### Dual Output Support
Simultaneous production to:
- File or stdout (`output_path`)
- Kafka (`kafka.conf` and `kafka.topic_conf`)

### Error Handling
- Validation errors: Caught and returned as `invalid` status
- Production errors: Caught and returned as `error` status
- Optional error event production via `mapToErrorEvent`
- Failed events converted to error events asynchronously (background processing)

### Hasty Mode
- `GET /v1/events?hasty=true` returns 202 immediately
- Useful when immediate persistence not required
- Events still processed asynchronously

## Configuration

### Schema Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `schema_uri_field` | `$schema` | Dotted path to schema URI in event (supports array for fallbacks) |
| `schema_base_uris` | undefined | Base URIs to prepend to relative schema URIs |
| `schema_file_extension` | undefined | File extension to append to schema URIs |

### Stream Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `stream_field` | undefined | Dotted path to stream name (uses sanitized schema URI if unset) |

### Output Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `output_path` | `stdout` | File path or 'stdout' for valid events |
| `kafka.conf` | undefined | node-rdkafka producer configuration |
| `kafka.topic_conf` | undefined | node-rdkafka topic configuration |

### Service Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `port` | 8888 | HTTP listener port |
| `interface` | `0.0.0.0` | HTTP listener interface |
| `user_agent` | `eventgate` | User-Agent for HTTP requests |
| `eventgate_factory_module` | `../lib/factories/default-eventgate` | Custom EventGate factory module path |
| `test_events` | undefined | Array of test events for readiness probe |
| `max_body_size` | `100kb` | Maximum request body size |

## Event Processing Flow

```
HTTP POST /v1/events
         ↓
Parse JSON event array
         ↓
For each event:
  1. Extract schema URI from event[schema_uri_field]
  2. Resolve schema URI (prepend base URIs, append extension)
  3. Load schema (from cache or HTTP/HTTPS/file)
  4. Compile validator (from cache or new compilation)
  5. Validate event against schema
  6. If valid: produce to output file and/or Kafka
  7. If invalid: record as invalid
         ↓
Group results by status (success/invalid/error)
         ↓
Optionally produce error events for failures
         ↓
Return appropriate HTTP status
```

## HTTP Response Codes

| Status | Meaning |
|--------|---------|
| 201 | All events successfully validated and produced |
| 202 | Events hastily received (processing may still be in progress) |
| 207 | Partial success (mix of success/failure) |
| 400 | All events invalid |
| 500 | Server error during processing (at least one error, may have successes) |

## Response Format

### 201/202 Success
No response body (status in status message)

### 207/400/500
```json
{
  "invalid": [
    {
      "status": "invalid",
      "event": { /* original event */ },
      "context": { /* validation errors */ }
    }
  ],
  "error": [
    {
      "status": "error",
      "event": { /* original event */ },
      "context": { "message": "error message" }
    }
  ]
}
```

## Custom Implementations

### EventGate Factory Module

Create a module exporting a `factory` function:

```javascript
async function factory(options, logger, metrics, router) {
    return new EventGate({
        validate: (event, context) => { /* custom validation */ },
        produce: (event, context) => { /* custom production */ },
        mapToErrorEvent: (error, event, context) => { /* optional error mapping */ }
    });
}
module.exports = { factory };
```

Configure in `config.yaml`:
```yaml
services:
  - name: eventgate
    eventgate_factory_module: ./my-custom-factory
```

### Using EventGate as a Dependency

```yaml
services:
  - name: eventgate-custom
    module: eventgate
    entrypoint: app
```

## Development & Testing

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
- `test/schemas/`: Test JSONSchemas for validation tests
- `test/utils/`: Test utilities and factory helpers

## Dependencies

### Core
- `express`: HTTP server
- `ajv`: JSONSchema validation
- `winston`: Logging
- `lodash`: Utility functions
- `body-parser`: JSON request parsing

### Optional
- `@wikimedia/node-rdkafka-factory`: Kafka production
- `@wikimedia/node-rdkafka-prometheus`: Kafka metrics

## Security Considerations

1. **Schema Security**: All non-meta schemas validated against `json-schema-secure` by default
2. **CSP**: Default Content Security Policy restricts external resources
3. **CORS**: Configurable CORS headers (default `*`)
4. **Input Size**: Configurable `max_body_size` limits (default 100kb)
5. **Error Exposure**: ValidationError details exposed, other errors sanitized to messages only

## File Structure

```
eventgate/
├── lib/
│   ├── factories/
│   │   └── default-eventgate.js    # Default EventGate factory
│   ├── EventValidator.js           # Schema validation engine
│   ├── eventgate.js                # Core EventGate class
│   ├── event-util.js               # Event utility functions
│   ├── error.js                    # Error classes
│   ├── api-util.js                 # API utilities
│   ├── util.js                     # General utilities
│   └── swagger-ui.js               # Swagger UI integration
├── routes/
│   ├── events.js                   # Event submission endpoint
│   ├── info.js                     # Service info endpoints
│   └── root.js                     # Root endpoint (spec/doc)
├── test/
│   ├── features/                   # Feature tests
│   ├── schemas/                    # Test schemas
│   └── utils/                      # Test utilities
├── app.js                          # Express app initialization
├── server.js                       # Service entry point
├── spec.yaml                       # OpenAPI specification
└── package.json                    # Dependencies and scripts
```

## Related Services

- **eventgate-wikimedia**: Wikimedia Foundation's custom implementation
- **service-template-node**: Base template for Wikimedia Node.js services
- **KafkaSSE**: Kafka to Server-Sent Events adapter (in this repository)
- **eventstreams**: Event streaming service (in this repository)

## References

- [README.md](eventgate/README.md) - Detailed usage and architecture documentation
- [spec.yaml](eventgate/spec.yaml) - OpenAPI specification
- [package.json](eventgate/package.json) - Full dependency list
