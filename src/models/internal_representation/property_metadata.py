# src/models/internal_representation/property_metadata.py

from dataclasses import dataclass
from enum import Enum


class WikibaseDatatype(str, Enum):
    WIKIBASE_ITEM = "wikibase-item"
    STRING = "string"
    TIME = "time"
    QUANTITY = "quantity"
    COMMONS_MEDIA = "commonsMedia"
    EXTERNAL_ID = "external-id"
    URL = "url"


@dataclass(frozen=True)
class PropertyMetadata:
    property_id: str           # "P17"
    datatype: WikibaseDatatype # wikibase-item
