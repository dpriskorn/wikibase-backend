# Change Notification and Event Streaming

## Event generation

Each successful revision publication emits an event:

{
  "entity_id": "Q123",
  "revision_id": 42,
  "timestamp": "...",
  "author_id": "...",
  "type": "entity_updated"
}

---

## Event transport

Kafka / PubSub / Pulsar

At-least-once delivery

Ordered per entity partition key

---

## Event consumers

Watchlist / subscription service

Recent changes feeds

Search indexers

Data dumps

External mirrors

MediaWiki never fans out writes.
