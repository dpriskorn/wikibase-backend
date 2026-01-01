import re
from enum import Enum


class Datatype(str, Enum):
    WIKIBASE_ITEM = "wikibase-item"
    STRING = "string"
    TIME = "time"
    QUANTITY = "quantity"
    GLOBOCOORDINATE = "globecoordinate"
    MONOLINGUALTEXT = "monolingualtext"
    EXTERNAL_ID = "external-id"
    COMMONS_MEDIA = "commonsMedia"
    GEO_SHAPE = "geo-shape"
    TABULAR_DATA = "tabular-data"
    MUSICAL_NOTATION = "musical-notation"
    URL = "url"
    MATH = "math"
    ENTITY_SCHEMA = "entity-schema"

    @classmethod
    def normalize_from_sparql(cls, datatype: str) -> str:
        """
        Normalize Wikidata SPARQL datatype CamelCase to kebab-case format.

        Converts:
          - WikibaseItem -> wikibase-item
          - CommonsMedia -> commonsmedia
          - ExternalId -> external-id
          - Url -> url
          - GlobeCoordinate -> globecoordinate
          etc.

        Args:
            datatype: Datatype name from SPARQL endpoint

        Returns:
            Normalized datatype string
        """
        special_mappings = {
            "ExternalId": "external-id",
            "WikibaseExternalId": "external-id",
            "Url": "url",
            "WikibaseUrl": "url",
            "CommonsMedia": "commonsmedia",
            "WikibaseCommonsMedia": "commonsmedia",
            "WikibaseEntitySchema": "entity-schema",
            "WikibaseGeoShape": "geo-shape",
            "WikibaseGlobeCoordinate": "globecoordinate",
            "WikibaseTabularData": "tabular-data",
            "WikibaseMusicalNotation": "musical-notation",
        }

        if datatype in special_mappings:
            return special_mappings[datatype]

        kebab = re.sub(r"([a-z])([A-Z])", r"\1-\2", datatype)
        return kebab.lower()
