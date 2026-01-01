from typing import TextIO
import hashlib

from models.rdf_builder.property_registry.models import PropertyShape, get_owl_type
from models.config.settings import settings


class PropertyOntologyWriter:
    @staticmethod
    def write_property_metadata(output: TextIO, shape: PropertyShape):
        """Write property metadata block with labels, descriptions, predicate links"""
        pid = shape.pid
        wd = f"wd:{pid}"

        output.write(f"{wd} a wikibase:Property ;\n")

        for lang, label_data in shape.labels.items():
            label = label_data.get("value", "")
            output.write(f'\trdfs:label "{label}"@{lang} ;\n')
            output.write(f'\tskos:prefLabel "{label}"@{lang} ;\n')
            output.write(f'\tschema:name "{label}"@{lang} ;\n')

        for lang, desc_data in shape.descriptions.items():
            description = desc_data.get("value", "")
            output.write(f'\tschema:description "{description}"@{lang} ;\n')

        datatype_uri = PropertyOntologyWriter._datatype_uri(shape.datatype)
        output.write(f"\twikibase:propertyType <{datatype_uri}> ;\n")

        output.write(f"\twikibase:directClaim wdt:{pid} ;\n")
        output.write(f"\twikibase:claim p:{pid} ;\n")
        output.write(f"\twikibase:statementProperty ps:{pid} ;\n")

        if shape.predicates.value_node:
            output.write(f"\twikibase:statementValue {shape.predicates.value_node} ;\n")
            output.write(f"\twikibase:qualifierValue pqv:{pid} ;\n")
            output.write(f"\twikibase:referenceValue prv:{pid} ;\n")

        if shape.predicates.statement_normalized:
            output.write(f"\twikibase:statementValueNormalized psn:{pid} ;\n")
        if shape.predicates.qualifier_normalized:
            output.write(f"\twikibase:qualifierValueNormalized pqn:{pid} ;\n")
        if shape.predicates.reference_normalized:
            output.write(f"\twikibase:referenceValueNormalized prn:{pid} ;\n")
        if shape.predicates.direct_normalized:
            output.write(f"\twikibase:directClaimNormalized wdtn:{pid} ;\n")

        output.write(f"\twikibase:qualifier pq:{pid} ;\n")
        output.write(f"\twikibase:reference pr:{pid} ;\n")
        output.write(f"\twikibase:novalue wdno:{pid} .\n")

    @staticmethod
    def _datatype_uri(datatype: str) -> str:
        """Convert datatype string to ontology URI"""
        return {
            "wikibase-item": "http://wikiba.se/ontology#WikibaseItem",
            "wikibase-string": "http://wikiba.se/ontology#String",
            "string": "http://wikiba.se/ontology#String",
            "external-id": "http://wikiba.se/ontology#ExternalId",
            "wikibase-monolingualtext": "http://wikiba.se/ontology#Monolingualtext",
            "monolingualtext": "http://wikiba.se/ontology#Monolingualtext",
            "commonsmedia": "http://wikiba.se/ontology#CommonsMedia",
            "commonsMedia": "http://wikiba.se/ontology#CommonsMedia",
            "globecoordinate": "http://wikiba.se/ontology#Globecoordinate",
            "globe-coordinate": "http://wikiba.se/ontology#Globecoordinate",
            "quantity": "http://wikiba.se/ontology#Quantity",
            "url": "http://wikiba.se/ontology#Url",
            "math": "http://wikiba.se/ontology#Math",
            "time": "http://wikiba.se/ontology#Time",
            "geo-shape": "http://wikiba.se/ontology#GeoShape",
            "geoshape": "http://wikiba.se/ontology#GeoShape",
            "tabular-data": "http://wikiba.se/ontology#TabularData",
            "tabulardata": "http://wikiba.se/ontology#TabularData",
        }.get(datatype, "http://wikiba.se/ontology#String")

    @staticmethod
    def write_property(output: TextIO, shape: PropertyShape):
        """Write property ontology with all predicate declarations"""
        pid = shape.pid
        output.write(f"p:{pid} a owl:ObjectProperty .\n")
        output.write(f"psv:{pid} a owl:ObjectProperty .\n")
        output.write(f"pqv:{pid} a owl:ObjectProperty .\n")
        output.write(f"prv:{pid} a owl:ObjectProperty .\n")
        output.write(f"wdt:{pid} a {get_owl_type(shape.datatype)} .\n")
        output.write(f"ps:{pid} a owl:ObjectProperty .\n")
        output.write(f"pq:{pid} a owl:ObjectProperty .\n")
        output.write(f"pr:{pid} a owl:ObjectProperty .\n")
        if shape.predicates.statement_normalized:
            output.write(f"psn:{pid} a owl:ObjectProperty .\n")
        if shape.predicates.qualifier_normalized:
            output.write(f"pqn:{pid} a owl:ObjectProperty .\n")
        if shape.predicates.reference_normalized:
            output.write(f"prn:{pid} a owl:ObjectProperty .\n")
        if shape.predicates.direct_normalized:
            output.write(f"wdtn:{pid} a owl:ObjectProperty .\n")

    @staticmethod
    def _generate_blank_node_id(property_id: str) -> str:
        """Generate stable blank node ID for property no-value

        Matches MediaWiki Wikibase algorithm from PropertySpecificComponentsRdfBuilder.php:
        md5(implode('-', ['owl:complementOf', $repositoryName, $localName]))

        For wikidata.org, repositoryName is 'wikidata' (default in settings)
        """
        repository_name = settings.wikibase_repository_name
        hash_input = f"owl:complementOf-{repository_name}-{property_id}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    @staticmethod
    def write_novalue_class(output: TextIO, property_id: str):
        """Write no-value class with OWL complement restriction"""
        blank_node_id = PropertyOntologyWriter._generate_blank_node_id(property_id)
        output.write(f"wdno:{property_id} a owl:Class ;\n")
        output.write(f"\towl:complementOf _:{blank_node_id} .\n")
        output.write(f"\n")
        output.write(f"_:{blank_node_id} a owl:Restriction ;\n")
        output.write(f"\towl:onProperty wdt:{property_id} ;\n")
        output.write(f"\towl:someValuesFrom owl:Thing .\n")
