from typing import Dict, Any

from rdflib import Namespace

WD = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")
WDS = Namespace("http://www.wikidata.org/entity/statement/")
WDV = Namespace("http://www.wikidata.org/value/")
WB = Namespace("http://wikiba.se/ontology#")

__all__ = ["serialize_entity_to_turtle"]

def serialize_entity_to_turtle(entity: Dict[str, Any], entity_id: str) -> str:
    from .serializer import serialize_entity_to_turtle as _serialize_entity_to_turtle
    return _serialize_entity_to_turtle(entity, entity_id)
