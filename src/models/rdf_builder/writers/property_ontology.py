from typing import TextIO
import hashlib


class PropertyOntologyWriter:
    @staticmethod
    def write_property(output: TextIO, property_id: str):
        """Write property ontology with all predicate declarations"""
        output.write(f'wd:{property_id} a wikibase:Property .\n')
        output.write(f'p:{property_id} a owl:ObjectProperty .\n')
        output.write(f'psv:{property_id} a owl:ObjectProperty .\n')
        output.write(f'pqv:{property_id} a owl:ObjectProperty .\n')
        output.write(f'prv:{property_id} a owl:ObjectProperty .\n')
        output.write(f'wdt:{property_id} a owl:ObjectProperty .\n')
        output.write(f'ps:{property_id} a owl:ObjectProperty .\n')
        output.write(f'pq:{property_id} a owl:ObjectProperty .\n')
        output.write(f'pr:{property_id} a owl:ObjectProperty .\n')

    @staticmethod
    def _generate_blank_node_id(property_id: str) -> str:
        """Generate stable blank node ID for property no-value"""
        hash_input = f"novalue-{property_id}"
        hash_bytes = hashlib.md5(hash_input.encode()).digest()
        return hash_bytes[:12].hex()

    @staticmethod
    def write_novalue_class(output: TextIO, property_id: str):
        """Write no-value class with OWL complement restriction"""
        blank_node_id = PropertyOntologyWriter._generate_blank_node_id(property_id)
        output.write(f'wdno:{property_id} a owl:Class ;\n')
        output.write(f'\towl:complementOf _:{blank_node_id} .\n')
        output.write(f'\n')
        output.write(f'_:{blank_node_id} a owl:Restriction ;\n')
        output.write(f'\towl:onProperty wdt:{property_id} ;\n')
        output.write(f'\towl:someValuesFrom owl:Thing .\n')

