from typing import Any

from .values.entity_value_parser import parse_entity_value
from .values.string_value_parser import parse_string_value
from .values.time_value_parser import parse_time_value
from .values.quantity_value_parser import parse_quantity_value
from .values.globe_value_parser import parse_globe_value
from .values.monolingual_value_parser import parse_monolingual_value
from .values.external_id_value_parser import parse_external_id_value
from .values.commons_media_value_parser import parse_commons_media_value
from .values.geo_shape_value_parser import parse_geo_shape_value
from .values.tabular_data_value_parser import parse_tabular_data_value
from .values.musical_notation_value_parser import parse_musical_notation_value
from .values.url_value_parser import parse_url_value
from .values.math_value_parser import parse_math_value
from .values.entity_schema_value_parser import parse_entity_schema_value
from .values.novalue_value_parser import parse_novalue_value
from .values.somevalue_value_parser import parse_somevalue_value
from services.shared.models.internal_representation.datatypes import Datatype
from services.shared.models.internal_representation.json_fields import JsonField


PARSERS = {
    "wikibase-entityid": parse_entity_value,
    Datatype.STRING.value: parse_string_value,
    "time": parse_time_value,
    "quantity": parse_quantity_value,
    "globecoordinate": parse_globe_value,
    "monolingualtext": parse_monolingual_value,
    Datatype.EXTERNAL_ID.value: parse_external_id_value,
    Datatype.COMMONS_MEDIA.value: parse_commons_media_value,
    Datatype.GEO_SHAPE.value: parse_geo_shape_value,
    Datatype.TABULAR_DATA.value: parse_tabular_data_value,
    Datatype.MUSICAL_NOTATION.value: parse_musical_notation_value,
    Datatype.URL.value: parse_url_value,
    Datatype.MATH.value: parse_math_value,
    Datatype.ENTITY_SCHEMA.value: parse_entity_schema_value,
}


def parse_value(snak_json: dict[str, Any]):
    snaktype = snak_json.get(JsonField.SNAKTYPE.value)
    
    if snaktype == "novalue":
        return parse_novalue_value()
    
    if snaktype == "somevalue":
        return parse_somevalue_value()
    
    if snaktype != JsonField.VALUE.value:
        raise ValueError(f"Only value snaks are supported, got snaktype: {snaktype}")

    datavalue = snak_json.get(JsonField.DATAVALUE.value, {})
    datatype = snak_json.get(JsonField.DATATYPE.value)
    datavalue_type = datavalue.get("type", datatype)

    parser = PARSERS.get(str(datatype)) or PARSERS.get(str(datavalue_type))
    if not parser:
        raise ValueError(f"Unsupported value type: {datavalue_type}, datatype: {datatype}")
    return parser(datavalue)
