import logging
from io import StringIO
from pathlib import Path
from typing import TextIO

from models.internal_representation.entity import Entity
from models.rdf_builder.models.rdf_statement import RDFStatement
from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.writers.triple import TripleWriters
from models.rdf_builder.writers.property_ontology import PropertyOntologyWriter
from models.rdf_builder.entity_cache import load_entity_metadata

logger = logging.getLogger(__name__)


class EntityConverter:
    """
    Converts internal Entity representation to RDF Turtle format.
    """

    def __init__(self, property_registry: PropertyRegistry, entity_metadata_dir: Path | None = None):
        self.properties = property_registry
        self.writers = TripleWriters()
        self.entity_metadata_dir = entity_metadata_dir

    def convert_to_turtle(self, entity: Entity, output: TextIO):
        """Convert entity to Turtle format."""
        self.writers.write_header(output)
        self._write_entity_metadata(entity, output)
        self._write_statements(entity, output)
        self._write_referenced_entity_metadata(entity, output)
        self._write_property_metadata(entity, output)

    def _write_entity_metadata(self, entity: Entity, output: TextIO):
        """Write entity type, labels, descriptions, aliases, sitelinks."""
        self.writers.write_entity_type(output, entity.id)
        self.writers.write_dataset_triples(output, entity.id)

        for lang, label in entity.labels.items():
            self.writers.write_label(output, entity.id, lang, label)

        for lang, description in entity.descriptions.items():
            self.writers.write_description(output, entity.id, lang, description)

        for lang, aliases in entity.aliases.items():
            for alias in aliases:
                self.writers.write_alias(output, entity.id, lang, alias)

        if entity.sitelinks:
            for site_key, sitelink_data in entity.sitelinks.items():
                self.writers.write_sitelink(output, entity.id, sitelink_data)

    def _write_statements(self, entity: Entity, output: TextIO):
        """Write all statements."""
        for stmt in entity.statements:
            rdf_stmt = RDFStatement(stmt)
            self._write_statement(entity.id, rdf_stmt, output)

    def _write_statement(self, entity_id: str, rdf_stmt: RDFStatement, output: TextIO):
        """Write single statement with references."""
        shape = self.properties.shape(rdf_stmt.property_id)
        logger.debug(f"Writing statement for {rdf_stmt.property_id}, shape: {shape}")
        self.writers.write_statement(output, entity_id, rdf_stmt, shape)

    def _write_property_metadata(self, entity: Entity, output: TextIO):
        """Write property metadata blocks for properties used in entity."""
        property_ids = set()

        for stmt in entity.statements:
            property_ids.add(stmt.property)

        for pid in sorted(property_ids):
            shape = self.properties.shape(pid)
            PropertyOntologyWriter.write_property_metadata(output, shape)
            PropertyOntologyWriter.write_property(output, shape)
            PropertyOntologyWriter.write_novalue_class(output, pid)

    def _collect_referenced_entities(self, entity: Entity) -> set[str]:
        """Collect unique entity IDs referenced in statement values."""
        referenced = set()
        for stmt in entity.statements:
            if stmt.value.kind == "entity":
                referenced.add(stmt.value.value)
        return referenced

    def _load_referenced_entity(self, entity_id: str) -> Entity:
        """Load entity metadata (labels, descriptions)."""
        from models.json_parser.entity_parser import parse_entity

        if not self.entity_metadata_dir:
            raise FileNotFoundError(f"No entity_metadata_dir set, cannot load {entity_id}")

        entity_json = load_entity_metadata(entity_id, self.entity_metadata_dir)
        return parse_entity(entity_json)

    def _write_referenced_entity_metadata(self, entity: Entity, output: TextIO):
        """Write metadata blocks for referenced entities."""
        if not self.entity_metadata_dir:
            return

        referenced_ids = self._collect_referenced_entities(entity)

        for entity_id in sorted(referenced_ids):
            ref_entity = self._load_referenced_entity(entity_id)

            self.writers.write_entity_type(output, ref_entity.id)

            for lang, label in ref_entity.labels.items():
                if label:
                    self.writers.write_label(output, ref_entity.id, lang, label)

            for lang, description in ref_entity.descriptions.items():
                if description:
                    self.writers.write_description(output, ref_entity.id, lang, description)

    def convert_to_string(self, entity: Entity) -> str:
        """Convert entity to Turtle string."""
        buf = StringIO()
        self.convert_to_turtle(entity, buf)
        return buf.getvalue()
