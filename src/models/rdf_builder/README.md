# Plan: Build RDF Generation from Internal Representation

## Overview

The parser is **COMPLETE** — it can read all Q42 data into internal models correctly.  
We now need to implement RDF generation from these internal models following **Wikibase RDF mapping rules**.

**Parser Status:** ✓ COMPLETE

### Verified capabilities

- ✓ Entity parsing (Entity model)
- ✓ Labels (72 languages in Q42)
- ✓ Descriptions (116 languages in Q42)
- ✓ Aliases (25 entries in Q42)
- ✓ Statements (332 statements across 293 properties)
- ✓ Qualifiers (nested in statements)
- ✓ References (nested in statements)
- ✓ Sitelinks (129 entries in Q42)
- ✓ All value types (entity, time, string, quantity, etc.)
- ✓ All ranks (normal, preferred, deprecated)
- ✓ All snaktypes (value, novalue, somevalue)

---

## RDF Generation: NOT IMPLEMENTED

- **Current state:** No RDF generation code exists
- **Target:** Generate Turtle format RDF from internal `Entity` model

---

## Architecture Overview

Based on `doc/ARCHITECTURE/JSON-RDF-CONVERTER.md`:

Entity (internal model)
↓
RDF Generator
↓
Triples (Turtle format)


---

4. Missing RDF Features
Looking at golden TTL, it has features we don't generate:
- Direct claim triples (lines 43-51): wdt:P17 wd:Q142 ;
- Value nodes (line 91): psv:P625 wdv:9f0355cb43b5be5caf0570c31d4fb707 ;
- BestRank (lines 54, 62, etc.): a wikibase:Statement, wikibase:BestRank ;
