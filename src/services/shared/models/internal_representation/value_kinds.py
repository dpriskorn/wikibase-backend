from enum import Enum


class ValueKind(str, Enum):
    ENTITY = "entity"
    STRING = "string"
    TIME = "time"
    QUANTITY = "quantity"
    GLOBE = "globe"
    MONOLINGUAL = "monolingual"
    EXTERNAL_ID = "external_id"
    COMMONS_MEDIA = "commons_media"
    GEO_SHAPE = "geo_shape"
    TABULAR_DATA = "tabular_data"
    MUSICAL_NOTATION = "musical_notation"
    URL = "url"
    MATH = "math"
    ENTITY_SCHEMA = "entity_schema"
    NOVALUE = "novalue"
    SOMEVALUE = "somevalue"
