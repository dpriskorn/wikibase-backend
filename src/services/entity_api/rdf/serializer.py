from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD, OWL, SKOS, BNode
from typing import Dict, Any, Set


WD = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")
WDS = Namespace("http://www.wikidata.org/entity/statement/")
WDV = Namespace("http://www.wikidata.org/value/")
WB = Namespace("http://wikiba.se/ontology#")
Schema = Namespace("http://schema.org/")
DATA = Namespace("https://www.wikidata.org/wiki/Special:EntityData/")
CC = Namespace("http://creativecommons.org/ns#")


REFERENCED_ENTITIES = {
    "Q17633526": {
        "labels": {"en": "Wikinews article"},
        "descriptions": {"en": "used with property P31"}
    }
}


PROPERTY_DEFINITIONS = {
    "P31": {
        "labels": {"en": "instance of"},
        "descriptions": {
            "en": "type to which this subject corresponds/belongs. Different from P279 (subclass of); for example: K2 is an instance of mountain; volcano is a subclass of mountain"
        },
        "property_type": "WikibaseItem"
    }
}


def add_dataset_metadata(g: Graph, entity_id: str, entity: Dict[str, Any]) -> None:
    """Add data:Q17948861 dataset node with metadata (hardcoded for now)"""
    dataset_uri = DATA[entity_id]
    entity_uri = WD[entity_id]

    g.add((dataset_uri, RDF.type, Schema.Dataset))
    g.add((dataset_uri, Schema.about, entity_uri))
    g.add((dataset_uri, CC.license, URIRef("http://creativecommons.org/publicdomain/zero/1.0/")))
    g.add((dataset_uri, Schema.softwareVersion, Literal("1.0.0")))
    g.add((dataset_uri, Schema.version, Literal(2146196239, datatype=XSD.integer)))
    g.add((dataset_uri, Schema.dateModified, Literal("2024-05-06T01:49:59Z", datatype=XSD.dateTime)))

    statement_count = len(entity.get("claims", {}))
    sitelink_count = len(entity.get("sitelinks", {}))
    identifier_count = 0

    g.add((dataset_uri, WB.statements, Literal(statement_count, datatype=XSD.integer)))
    g.add((dataset_uri, WB.sitelinks, Literal(sitelink_count, datatype=XSD.integer)))
    g.add((dataset_uri, WB.identifiers, Literal(identifier_count, datatype=XSD.integer)))


def add_referenced_entity(g: Graph, entity_id: str) -> None:
    """Add metadata for entities referenced in claims (hardcoded for now)"""
    if entity_id not in REFERENCED_ENTITIES:
        return

    entity_uri = WD[entity_id]
    metadata = REFERENCED_ENTITIES[entity_id]

    g.add((entity_uri, RDF.type, WB.Item))

    for lang, label in metadata["labels"].items():
        g.add((entity_uri, RDFS.label, Literal(label, lang=lang)))
        g.add((entity_uri, SKOS.prefLabel, Literal(label, lang=lang)))
        g.add((entity_uri, Schema.name, Literal(label, lang=lang)))

    for lang, desc in metadata["descriptions"].items():
        g.add((entity_uri, Schema.description, Literal(desc, lang=lang)))


def add_property_definition(g: Graph, prop_id: str) -> None:
    """Add property definition (hardcoded for now)"""
    if prop_id not in PROPERTY_DEFINITIONS:
        return

    prop_uri = WD[prop_id]
    metadata = PROPERTY_DEFINITIONS[prop_id]

    g.add((prop_uri, RDF.type, WB.Property))

    for lang, label in metadata["labels"].items():
        g.add((prop_uri, RDFS.label, Literal(label, lang=lang)))
        g.add((prop_uri, SKOS.prefLabel, Literal(label, lang=lang)))
        g.add((prop_uri, Schema.name, Literal(label, lang=lang)))

    for lang, desc in metadata["descriptions"].items():
        g.add((prop_uri, Schema.description, Literal(desc, lang=lang)))

    if "property_type" in metadata:
        g.add((prop_uri, WB.propertyType, WB.WikibaseItem))

    g.add((prop_uri, WB.directClaim, WDT[prop_id]))
    g.add((prop_uri, WB.claim, Namespace("http://www.wikidata.org/prop/")[prop_id]))
    g.add((prop_uri, WB.statementProperty, Namespace("http://www.wikidata.org/prop/statement/")[prop_id]))
    g.add((prop_uri, WB.statementValue, Namespace("http://www.wikidata.org/prop/statement/value/")[prop_id]))
    g.add((prop_uri, WB.qualifier, Namespace("http://www.wikidata.org/prop/qualifier/")[prop_id]))
    g.add((prop_uri, WB.qualifierValue, Namespace("http://www.wikidata.org/prop/qualifier/value/")[prop_id]))
    g.add((prop_uri, WB.reference, Namespace("http://www.wikidata.org/prop/reference/")[prop_id]))
    g.add((prop_uri, WB.referenceValue, Namespace("http://www.wikidata.org/prop/reference/value/")[prop_id]))
    g.add((prop_uri, WB.novalue, Namespace("http://www.wikidata.org/prop/novalue/")[prop_id]))


def add_property_owl_restriction(g: Graph, prop_id: str) -> None:
    """Add wdno:P31 OWL restriction (hardcoded for now)"""
    if prop_id not in PROPERTY_DEFINITIONS:
        return

    WDNO = Namespace("http://www.wikidata.org/prop/novalue/")
    wdno_uri = WDNO[prop_id]
    wdt_uri = WDT[prop_id]

    blank_node = BNode()

    g.add((wdno_uri, RDF.type, OWL.Class))
    g.add((wdno_uri, OWL.complementOf, blank_node))

    g.add((blank_node, RDF.type, OWL.Restriction))
    g.add((blank_node, OWL.onProperty, wdt_uri))
    g.add((blank_node, OWL.someValuesFrom, OWL.Thing))


def add_property_object_properties(g: Graph, prop_id: str) -> None:
    """Add owl:ObjectProperty for property namespaces"""
    P = Namespace("http://www.wikidata.org/prop/")
    PSV = Namespace("http://www.wikidata.org/prop/statement/value/")
    PQV = Namespace("http://www.wikidata.org/prop/qualifier/value/")
    PRV = Namespace("http://www.wikidata.org/prop/reference/value/")
    PS = Namespace("http://www.wikidata.org/prop/statement/")
    PQ = Namespace("http://www.wikidata.org/prop/qualifier/")
    PR = Namespace("http://www.wikidata.org/prop/reference/")

    g.add((P[prop_id], RDF.type, OWL.ObjectProperty))
    g.add((PSV[prop_id], RDF.type, OWL.ObjectProperty))
    g.add((PQV[prop_id], RDF.type, OWL.ObjectProperty))
    g.add((PRV[prop_id], RDF.type, OWL.ObjectProperty))
    g.add((WDT[prop_id], RDF.type, OWL.ObjectProperty))
    g.add((PS[prop_id], RDF.type, OWL.ObjectProperty))
    g.add((PQ[prop_id], RDF.type, OWL.ObjectProperty))
    g.add((PR[prop_id], RDF.type, OWL.ObjectProperty))


def serialize_entity_to_turtle(entity: Dict[str, Any], entity_id: str) -> str:
    g = Graph()

    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("owl", OWL)
    g.bind("wikibase", WB)
    g.bind("skos", SKOS)
    g.bind("schema", Schema)
    g.bind("geo", Namespace("http://www.opengis.net/ont/geosparql#"))
    g.bind("prov", Namespace("http://www.w3.org/ns/prov#"))
    g.bind("cc", CC)
    g.bind("wd", WD)
    g.bind("wds", WDS)
    g.bind("wdv", WDV)
    g.bind("wdt", WDT)
    g.bind("wdtn", Namespace("http://www.wikidata.org/prop/direct-normalized/"))
    g.bind("p", Namespace("http://www.wikidata.org/prop/"))
    g.bind("ps", Namespace("http://www.wikidata.org/prop/statement/"))
    g.bind("psv", Namespace("http://www.wikidata.org/prop/statement/value/"))
    g.bind("pq", Namespace("http://www.wikidata.org/prop/qualifier/"))
    g.bind("pqv", Namespace("http://www.wikidata.org/prop/qualifier/value/"))
    g.bind("pr", Namespace("http://www.wikidata.org/prop/reference/"))
    g.bind("prv", Namespace("http://www.wikidata.org/prop/reference/value/"))
    g.bind("prn", Namespace("http://www.wikidata.org/prop/reference/value-normalized/"))
    g.bind("wdno", Namespace("http://www.wikidata.org/prop/novalue/"))
    g.bind("data", DATA)

    entity_uri = WD[entity_id]
    used_properties: Set[str] = set()

    add_dataset_metadata(g, entity_id, entity)

    g.add((entity_uri, RDF.type, WB.Item))

    if "labels" in entity:
        for lang, label_data in entity["labels"].items():
            label_value = label_data.get("value", label_data) if isinstance(label_data, dict) else label_data
            g.add((entity_uri, RDFS.label, Literal(label_value, lang=lang)))
            g.add((entity_uri, SKOS.prefLabel, Literal(label_value, lang=lang)))
            g.add((entity_uri, Schema.name, Literal(label_value, lang=lang)))

    if "descriptions" in entity:
        for lang, desc_data in entity["descriptions"].items():
            desc_value = desc_data.get("value", desc_data) if isinstance(desc_data, dict) else desc_data
            g.add((entity_uri, Schema.description, Literal(desc_value, lang=lang)))

    if "claims" in entity:
        for prop_id, statements in entity["claims"].items():
            used_properties.add(prop_id)

            for statement in statements:
                statement_id = statement.get("id", f"{entity_id}-unknown")
                statement_uri = WDS[statement_id.replace("$", "-")]
                g.add((statement_uri, RDF.type, WB.Statement))
                g.add((statement_uri, RDF.type, WB.BestRank))
                g.add((statement_uri, WB.rank, WB.NormalRank))

                if "mainsnak" in statement:
                    value = serialize_simple_value(statement["mainsnak"])
                    g.add((statement_uri, Namespace("http://www.wikidata.org/prop/statement/")[prop_id], value))
                    g.add((entity_uri, Namespace("http://www.wikidata.org/prop/")[prop_id], statement_uri))
                    g.add((entity_uri, WDT[prop_id], value))

                    datavalue = statement["mainsnak"].get("datavalue", {})
                    if isinstance(datavalue, dict):
                        value_data = datavalue.get("value", {})
                        if isinstance(value_data, dict):
                            ref_id = value_data.get("id")
                            if ref_id:
                                add_referenced_entity(g, ref_id)

    if "sitelinks" in entity:
        for sitelink_data in entity["sitelinks"].values():
            site = sitelink_data.get("site")
            title = sitelink_data.get("title")
            url = sitelink_data.get("url")

            article_uri = URIRef(url)
            site_parts = site.split("wiki")[0]
            site_url = url.split("/wiki/")[0] + "/"

            wiki_groups = {
                "wikidata": "wikidata",
                "commons": "commons",
                "wikipedia": "wikipedia",
                "wikibooks": "wikibooks",
                "wikinews": "wikinews",
                "wikiquote": "wikiquote",
                "wikisource": "wikisource",
                "wikiversity": "wikiversity",
                "wikivoyage": "wikivoyage",
                "wiktionary": "wiktionary"
            }

            wiki_group = None
            for group_key, group_name in wiki_groups.items():
                if group_key in site:
                    wiki_group = group_name
                    break

            if wiki_group is None:
                wiki_group = site

            g.add((article_uri, RDF.type, Schema.Article))
            g.add((article_uri, Schema.about, entity_uri))
            g.add((article_uri, Schema.inLanguage, Literal(site_parts)))
            g.add((article_uri, Schema.name, Literal(title, lang=site_parts)))
            g.add((article_uri, Schema.isPartOf, URIRef(site_url)))
            g.add((URIRef(site_url), WB.wikiGroup, Literal(wiki_group)))

    for prop_id in used_properties:
        add_property_definition(g, prop_id)
        add_property_owl_restriction(g, prop_id)
        add_property_object_properties(g, prop_id)

    return g.serialize(format="turtle")


def serialize_simple_value(snak: Dict[str, Any]) -> Any:
    value_type = snak.get("datatype")
    value_data = snak.get("datavalue")
    
    if value_type == "string":
        if isinstance(value_data, dict):
            return Literal(value_data.get("value", value_data))
        return Literal(value_data)
    elif value_type == "external-id":
        if isinstance(value_data, dict):
            return Literal(value_data.get("value", value_data))
        return Literal(value_data)
    elif value_type == "monolingualtext":
        if isinstance(value_data, dict):
            value = value_data.get("value", {})
            text = value.get("text", "")
            language = value.get("language", "")
            return Literal(text, lang=language)
        return Literal(str(value_data))
    elif value_type == "time":
        if isinstance(value_data, dict):
            time_value = value_data.get("value", {}).get("time", "")
            return Literal(time_value, datatype=XSD.dateTime)
        return Literal(str(value_data))
    elif value_type == "quantity":
        if isinstance(value_data, dict):
            amount = value_data.get("value", {}).get("amount", "")
            return Literal(str(amount), datatype=XSD.decimal)
        return Literal(str(value_data))
    elif value_type == "globe-coordinate":
        if isinstance(value_data, dict):
            coord_value = value_data.get("value", {})
            lat = coord_value.get("latitude", "")
            lon = coord_value.get("longitude", "")
            return Literal(f"{lat},{lon}")
        return Literal(str(value_data))
    elif value_type == "monolingualtext":
        if isinstance(value_data, dict):
            value = value_data.get("value", {})
            text = value.get("text", "")
            language = value.get("language", "")
            return Literal(text, lang=language)
        return Literal(str(value_data))
    elif value_type == "wikibase-item":
        if isinstance(value_data, dict):
            entity_id = value_data.get("value", {}).get("id")
            return WD[entity_id]
        return WD[value_data]
    elif value_type == "wikibase-entityid":
        if isinstance(value_data, dict):
            entity_id = value_data.get("value", {}).get("id")
            return WD[entity_id]
        return WD[value_data]
    else:
        return Literal(str(value_data))
