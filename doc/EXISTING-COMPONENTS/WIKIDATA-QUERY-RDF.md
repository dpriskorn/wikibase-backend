# Wikidata Query RDF

The Wikidata Query Service is the Wikimedia implementation of a SPARQL server, based on the Blazegraph engine, designed to service queries for Wikidata and other datasets.

## Core Functionality

- SPARQL 1.1 compliant triple store for querying RDF data
- Real-time streaming updates from Wikibase instances via Kafka
- Efficient Blazegraph extensions optimized for Wikibase querying
- MediaWiki OAuth proxy for authenticated queries
- Tools for syncing Wikibase instances with SPARQL triple stores

## Modules

| Module | Description | License |
|--------|-------------|---------|
| `blazegraph` | Blazegraph extensions for efficient Wikibase querying | GPLv2 |
| `war` | Blazegraph service configurations | GPLv2 |
| `tools` | Sync tools for Wikibase ↔ SPARQL store integration | Apache 2.0 |
| `streaming-updater-producer` | Kafka producer for real-time updates (Flink) | Apache 2.0 |
| `streaming-updater-consumer` | Kafka consumer for update processing (Flink) | Apache 2.0 |
| `streaming-updater-common` | Shared streaming code | Apache 2.0 |
| `mw-oauth-proxy` | MediaWiki OAuth authentication proxy | Apache 2.0 |
| `rdf-spark-tools` | Spark-based RDF processing utilities | Apache 2.0 |
| `common` | Shared utilities across modules | Apache 2.0 |
| `testTools` | Testing helpers | Apache 2.0 |
| `dist` | Service deployment scripts | Apache 2.0 |

## Technology Stack

- **Java 8+** with Maven build system
- **Blazegraph 2.1.6** - RDF database
- **Apache Flink 1.17.1** - Stream processing
- **Apache Kafka 3.2.3** - Event streaming
- **Apache Spark 2.4.4** - Batch processing
- **Jetty 9.4.12** - Servlet container

## Key Features

- Real-time query service with sub-second response times
- Federation with external SPARQL endpoints
- Linked Data Fragments support
- Custom Wikibase optimizers for improved query performance
- Rate limiting and query throttling
- Comprehensive logging and metrics

## Development

Built as a multi-module Maven project with:

- **Unit tests** (no external dependencies) - classes ending in `UnitTest`
- **Integration tests** (Blazegraph, Kafka) - classes ending in `IntegrationTest`
- **RandomizedRunner** for property-based testing
- **Spotless** for code formatting

### Running Locally

```bash
cd wikidata-query-rdf
mvn -pl war jetty:run
```

Service will be available on port 9999.

### Testing

```bash
# Run unit tests
mvn test

# Run integration tests
mvn verify
```

## Documentation

- [User Manual](https://www.mediawiki.org/wiki/Wikidata_query_service/User_Manual) - Complete usage guide
- [Original README](./wikidata-query-rdf/README.md) - Detailed development notes
