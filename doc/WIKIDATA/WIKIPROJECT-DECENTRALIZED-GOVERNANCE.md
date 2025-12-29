# WikiProjects as Decentralized Governance

This document summarizes the proposal to reimagine WikiProjects as subcommunities that govern a subgraph or collection of items.

**Source**: [Wikidata:WikiProject Limits of Wikidata/WikiProjects as decentralized governance](https://www.wikidata.org/wiki/Wikidata:WikiProject_Limits_of_Wikidata/WikiProjects_as_decentralized_governance)

## New Concepts

- **Locked item**: An item that has been locked from any edits
- **Mass edit protected item**: An item that has been locked from any mass-edits by tools (trusted members of WikiProjects can be allowed to edit these items)
- **Archived item**: An item that has been archived (implies locked from any edits until unarchived). Works as a normal item but cannot be edited and can be excluded from weekly batches or downstream consumers that do not want stale knowledge
- **Dangling item**: An item that has no [maintained by WikiProject (P6104)](https://www.wikidata.org/wiki/Property:P6104) statement
- **Healthy WikiProject**: A WikiProject that:
  1. is responsive to Wikidata community admin requests and inquiries
  2. maintains their items in a way that is acceptable to the wider Wikidata community
  3. has at least 2 members

## Visions

### Wikidata
A Wikidata where there are no dangling items and all able humans can share in the sum of all knowledge in a socially viable and responsible way.

### WikiProjects
A healthy and thriving community of WikiProjects curate and maintain a wealth of knowledge together towards the Wikidata vision.

## Role of WikiProjects

### Current Role
- Weak definition and mandate
- Community of practice but with no decision power when it comes to item curation

### Suggested Role
- Power over items that fall under their sole curation responsibility
- Shared power over items that fall under shared curation responsibility (when 2 or more WikiProjects curate an item)
- Can decide to lock items from mass-edits (e.g. only certain users can mass-edit)
- Can request archival of items under their care if they no longer wish to curate them
- Adopt dangling items

## Role of Admins

### Wikidata Level
- Handle request for archiving of items because of dormant WikiProject
- Handle request for unarchiving of items because of revitalized WikiProject
- Archive or unarchive items

### WikiProject Level
- Handle mass edit protections of items (this ensures that the subgraph is stable and mass-edits are only performed by trusted community members in a responsible way)
- Handle semi-protections of items from vandalism

## Challenges

### Items Curated by Multiple WikiProjects
If 2 or more WikiProjects are set on an item, the WikiProjects must cooperate on decisions involving shared items.

### Dangling Items
A lot of dangling items is bad for Wikidata as a whole. It means that nobody is maintaining the knowledge and it is slowly rotting in place. On a community level, we should strive to archive all dangling items and keep them under 1% at all times.

### Vandalism
In a Wikidata with 1bn+ items, vandalism cannot be handled centrally. The WikiProjects have the responsibility of maintaining their items and keeping them up to date and free of vandalism is a very important part of this.

The Wikidata community can decide to archive items if a WikiProject is dysfunctional and not contributing to the overall vision.
