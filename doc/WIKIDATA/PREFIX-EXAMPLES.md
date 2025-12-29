```markdown
| Prefix     | Full URL                     | Usage                                                                 | Example |
|------------|------------------------------|-----------------------------------------------------------------------|---------|
| `wikibase:` | `http://wikiba.se/ontology#` | Wikibase ontology                                                      | `wd:Q2 a wikibase:Item` |

### Nodes

| Prefix   | Full URL               | Usage                                   | Example |
|----------|------------------------|-----------------------------------------|---------|
| `wdata:` | `/Special:EntityData/` | Data set describing a certain entity    | `wdata:Q2 schema:about wd:Q2 .` |
| `wd:`    | `/entity/`             | Wikibase entity (item or property)      | `wd:Q2 p:P9 wds:Q2-82a6e009-4f93-28dc-3555-38bbfc3afe6a` |
| `wds:`   | `/entity/statement/`   | Statement node, describes a claim       | `wds:Q2-a4078553-4ec1-a64a-79e7-c5b5e17b2782 a wikibase:Statement` |
| `wdv:`   | `/value/`              | Value node                              | `wdv:87d0dc1c7847f19ac0f19be978015dfb202cf59a a wikibase:Value` |
| `wdref:` | `/reference/`          | Reference node                          | `wds:Q3-24bf3704-4c5d-083a-9b59-1881f82b6b37 prov:wasDerivedFrom wdref:87d0dc1c7847f19ac0f19be978015dfb202cf59a .`<br>`wdref:87d0dc1c7847f19ac0f19be978015dfb202cf59a a wikibase:Reference .` |

### Predicates

| Prefix  | Full URL                           | Usage                                                                 | Example |
|---------|------------------------------------|-----------------------------------------------------------------------|---------|
| `wdt:`  | `/prop/direct/`                    | Truthy assertions linking entity directly to value                    | `wd:Q2 wdt:P9 <http://acme.com/>` |
| `wdtn:` | `/prop/direct-normalized/`         | Truthy assertions linking entity to normalized value                  | `wd:Q2 wdtn:P9 <http://acme.com/ABCDE>` |
| `p:`    | `/prop/`                           | Links entity to statement                                              | `wd:Q2 p:P9 wds:Q2-82a6e009-4f93-28dc-3555-38bbfc3afe6awd` |
| `wdno:` | `/prop/novalue/`                   | Class used when the entity has no value for this property              | `wd:Q2 a wdno:P9 .` |
| `ps:`   | `/prop/statement/`                 | Links value to statement                                               | `wds:Q3-24bf3704-4c5d-083a-9b59-1881f82b6b37 ps:P8 "-13000000000-01-01T00:00:00Z"^^xsd:dateTime` |
| `psv:`  | `/prop/statement/value/`           | Links deep value to statement                                          | `wds:Q3-24bf3704-4c5d-083a-9b59-1881f82b6b37 psv:P8 wdv:87d0dc1c7847f19ac0f19be978015dfb202cf59a` |
| `psn:`  | `/prop/statement/value-normalized/`| Links normalized value to statement                                    | `wds:Q3-24bf3704-4c5d-083a-9b59-1881f82b6b37 psn:P8 wdv:87d0dc1c7847f19ac0f19be978015dfb202cf59a` |
| `pq:`   | `/prop/qualifier/`                 | Links qualifier to statement                                           | `wds:Q3-24bf3704-4c5d-083a-9b59-1881f82b6b37 pq:P8 "-13000000000-01-01T00:00:00Z"^^xsd:dateTime` |
| `pqv:`  | `/prop/qualifier/value/`           | Links qualifier deep value to statement                                | `wds:Q3-24bf3704-4c5d-083a-9b59-1881f82b6b37 pqv:P8 wdv:87d0dc1c7847f19ac0f19be978015dfb202cf59a` |
| `pqn:`  | `/prop/qualifier/value-normalized/`| Links normalized qualifier value to statement                          | `wds:Q3-24bf3704-4c5d-083a-9b59-1881f82b6b37 pqn:P8 wdv:87d0dc1c7847f19ac0f19be978015dfb202cf59a` |
| `pr:`   | `/prop/reference/`                 | Links reference to value                                               | `wdref:87d0dc1c7847f19ac0f19be978015dfb202cf59a pr:P8 "-13000000000-01-01T00:00:00Z"^^xsd:dateTime` |
| `prv:`  | `/prop/reference/value/`           | Links reference to deep value                                          | `wdref:87d0dc1c7847f19ac0f19be978015dfb202cf59a prv:P8 wdv:87d0dc1c7847f19ac0f19be978015dfb202cf59a` |
| `prn:`  | `/prop/reference/value-normalized/`| Links reference to normalized value                                    | `wdref:87d0dc1c7847f19ac0f19be978015dfb202cf59a prn:P8 wdv:87d0dc1c7847f19ac0f19be978015dfb202cf59a` |
```
