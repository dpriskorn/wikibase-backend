# EventBus Extension

MediaWiki extension that produces change events to the Wikimedia Event Platform, enabling real-time propagation of wiki state changes to external systems.

## Overview

EventBus is a MediaWiki extension that acts as the producer client for the Wikimedia Event Platform. It captures state changes in MediaWiki (pages, revisions, users, etc.) and publishes them as JSON events to EventGate/EventBus services for consumption by downstream services like the Streaming Updater, analytics pipelines, and search indexing.

**Note:** This is an interim solution pending atomic event delivery in MediaWiki core. Events may fail to be delivered after MediaWiki commits changes, so it doesn't provide the reliability level targeted for production use. See [T120242](https://phabricator.wikimedia.org/T120242).

## Architecture

```
MediaWiki Hooks (PageSaveComplete, PageDeleteComplete, etc.)
                ↓
        HookHandlers / DomainEventIngresses
                ↓
        Event Serializers
                ↓
        EventBus (HTTP client)
                ↓
    EventGate/EventBus (Event Intake Service)
                ↓
           Kafka Topics
                ↓
     Downstream Consumers
```

## Core Components

### EventBus.php
Main event delivery client that:
- Sends events to event intake services via HTTP POST
- Handles event batching and partitioning for large payloads
- Manages HTTP timeouts, retries, and error handling
- Emits comprehensive metrics via StatsLib
- Supports multiple event types (TYPE_EVENT, TYPE_JOB, TYPE_PURGE)
- Forwards X-Client-IP header when configured

### EventBusFactory.php
Factory pattern for creating EventBus instances:
- `getInstance($eventServiceName)` - Get instance for configured service
- `getInstanceForStream($stream)` - Look up service from EventStreamConfig
- Singleton instances per event service name

### StreamNameMapper.php
Maps stream names for different deployment scenarios:
- Allows separate streams for private vs public wikis
- Enables different stream names for testing/staging environments
- Maps `mediawiki.page_change.v1` to production or test streams

### EventFactory.php
Creates event objects with required fields:
- `$schema` - JSON schema URI
- `meta` - Event metadata (stream, domain, dt, request_id)
- Tags event with proper timestamp and request ID

### EventBusSendUpdate.php
Deferrable update wrapper for:
- Automatic event batching
- Single HTTP request for multiple events
- Deferred execution to avoid blocking main request

### Event Serializers
Convert MediaWiki objects to event JSON:

**MediaWikiEntitySerializers:**
- `PageChangeEventSerializer` - Page revision, deletion, move events
- `PageEntitySerializer` - Page metadata
- `RevisionEntitySerializer` - Revision metadata
- `RevisionSlotEntitySerializer` - Revision slot content
- `UserEntitySerializer` - User account info

### HookHandlers
MediaWiki hook integrations that produce events:

**EventBusHooks** (deprecated, being replaced):
- PageSaveComplete - Page edit events
- PageDeleteComplete - Page deletion
- PageMoveComplete - Page rename
- PageUndeleteComplete - Page restoration
- ArticleRevisionVisibilitySet - Revision visibility changes
- ArticlePurge - Cache purge events
- LinksUpdateComplete - Backlink updates
- BlockIpComplete - User blocks
- ChangeTagsAfterUpdateTags - Tag changes
- RevisionRecordInserted - New revisions

**PageChangeEventIngress** (new DomainEventIngress):
- Listens to DomainEventEvents
- PageRevisionUpdated, PageDeleted, PageMoved
- PageCreated, PageHistoryVisibilityChanged

**CampaignChangeHooks:**
- CentralNotice campaign changes

### Adapters
Integration points for other MediaWiki subsystems:

**EventBusMonologHandler:**
- Sends log messages as events to EventBus
- Converts log levels to event fields
- Useful for centralized log aggregation

**EventBusRCFeedEngine/Formatter:**
- RecentChanges feed via EventBus
- Publishes to `mediawiki.recentchange` stream
- Replaces traditional RC feed formats

**CdnPurgeEventRelayer:**
- Forwards CDN purge events to EventBus
- Integrates with HTCPPurger

**JobQueueEventBus:**
- Serializes MediaWiki jobs as events
- Enables job processing by external services

### REST API
**RunSingleJobHandler:**
- Endpoint: `/eventbus/v0/internal/job/execute`
- Executes single MediaWiki job from external event
- Allows job queue operations via EventBus

## Configuration

### Event Services Definition

Configure event intake endpoints via `$wgEventServices`:

```php
$wgEventServices = [
    'eventgate-analytics' => [
        'url' => 'http://eventgate-analytics:8192/v1/events',
        'timeout' => 5,
    ],
    'eventgate-main' => [
        'url' => 'http://eventgate-main:8192/v1/events',
        'timeout' => 5,
    ],
];
```

### Stream Configuration

Per-stream settings via `$wgEventStreams`:

```php
$wgEventStreams = [
    'mediawiki.page_change.v1' => [
        'producers' => [
            'mediawiki_eventbus' => [
                'event_service_name' => 'eventgate-main',
                'enabled' => true,
            ],
        ],
    ],
];
```

### Global Settings

| Setting | Description | Default |
|---------|-------------|----------|
| `$wgEnableEventBus` | Event types to produce (TYPE_NONE\|TYPE_EVENT\|TYPE_JOB\|TYPE_PURGE\|TYPE_ALL) | TYPE_NONE |
| `$wgEventServiceDefault` | Default event service name | eventbus |
| `$wgEventBusMaxBatchByteSize` | Max batch size in bytes | 4194304 (4MB) |
| `$wgEventBusStreamNamesMap` | Stream name mapping for custom deployments | {} |
| `$wgEventBusEnableRunJobAPI` | Enable REST job execution API | true |

### Event Types

- **TYPE_EVENT (1)** - Regular MediaWiki events (page changes, edits, etc.)
- **TYPE_JOB (2)** - Serialized MediaWiki jobs
- **TYPE_PURGE (4)** - CDN purge events
- **TYPE_NONE (0)** - Disabled
- **TYPE_ALL (7)** - All event types enabled

## Stream Examples

**Core MediaWiki Streams:**
- `mediawiki.page_change.v1` - Page edits, creates, deletes, moves
- `mediawiki.revision_create.v1` - New revisions
- `mediawiki.recentchange` - RecentChanges feed
- `mediawiki.page_delete.v1` - Page deletions
- `mediawiki.page_restore.v1` - Page restorations

**Derived Streams:**
- `mediawiki.revision-tags-change.v1` - Tag changes on revisions
- `resource_change` - Resource changes (images, media)

## RCFeed Integration

Configure RC feed to use EventBus:

```php
use MediaWiki\Extension\EventBus\Adapters\RCFeed\EventBusRCFeedEngine;
use MediaWiki\Extension\EventBus\Adapters\RCFeed\EventBusRCFeedFormatter;

$wgRCFeeds['eventgate-main'] = [
    'class' => EventBusRCFeedEngine::class,
    'formatter' => EventBusRCFeedFormatter::class,
    'eventServiceName' => 'eventgate-main',
];
```

## Event Lifecycle

1. **Trigger**: MediaWiki action occurs (edit, delete, etc.)
2. **Hook Execution**: MediaWiki hook fires (e.g., PageSaveComplete)
3. **Event Creation**: Hook handler builds event object
4. **Serialization**: EventSerializer converts to JSON
5. **Batching**: EventBusSendUpdate queues events
6. **Delivery**: EventBus.send() POSTs to EventGate
7. **Validation**: EventGate validates against JSON schema
8. **Ingestion**: Valid events published to Kafka
9. **Consumption**: Downstream services process events

## Metrics

StatsLib metrics emitted:

**Delivery Metrics:**
- `events_outgoing_total` - Events sent
- `events_outgoing_by_stream_total` - Per-stream outgoing
- `events_accepted_total` - Events accepted by service
- `events_failed_total` - Failed events by failure_kind
- `events_failed_by_stream_total` - Failed per stream
- `event_service_response_total` - HTTP response codes
- `event_batch_not_enqueable_total` - Disabled event types
- `event_batch_is_string_total` - String input deprecation
- `event_batch_not_serializable_total` - JSON encode failures
- `event_batch_partitioned_total` - Large batch splits

## Error Handling

### HTTP Response Codes
- **201** - All events accepted and persisted
- **202** - All events accepted (hasty response)
- **207** - Partial success (some events failed validation)
- **400** - All events failed schema validation
- **500+** - Service error

### Retry Logic
- MultiHttpClient handles connection errors
- Configurable timeout (default: 10s)
- Failed events logged with detailed context
- Metrics track all failures

## Testing

```bash
# Run PHP tests
composer test

# Run phan type checking
composer phan

# Run tests and linters
composer fix
```

**Test files:**
- `tests/phpunit/unit/` - Unit tests
- `tests/phpunit/integration/` - Integration tests
- `tests/api-testing/` - API endpoint tests

## Technology Stack

- **PHP** - Extension language
- **MediaWiki 1.46+** - Required MediaWiki version
- **EventGate** - Event intake service
- **Kafka** - Underlying message bus
- **Wikimedia StatsLib** - Metrics
- **Wikimedia MultiHttpClient** - HTTP client

## Dependencies

**Production:**
- `mediawiki/core` - MediaWiki framework
- `wikimedia/http-request-timeout` - HTTP utilities
- `wikimedia/statslib` - Metrics

**Development:**
- `mediawiki/mediawiki-codesniffer` - Code style
- `mediawiki/mediawiki-phan-config` - Static analysis
- `mediawiki/minus-x` - Permissions checker

## License

GNU General Public License 2.0 or later

## References

- [Event Platform Documentation](https://wikitech.wikimedia.org/wiki/Event_Platform)
- [EventGate](https://wikitech.wikimedia.org/wiki/Event_Platform/EventGate)
- [EventStreamConfig Extension](https://wikitech.wikimedia.org/wiki/Event_Platform/Stream_Configuration)
- [Reliable Event Bus Task](https://phabricator.wikimedia.org/T84923)
- [EventBus Integration Task](https://phabricator.wikimedia.org/T116786)
