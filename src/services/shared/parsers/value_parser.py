from typing import Any

from pydantic import ValidationError

from ..models.internal_representation.values import (
    EntityValue,
    StringValue,
    TimeValue,
    QuantityValue,
    GlobeValue,
    MonolingualValue,
    ExternalIDValue,
    CommonsMediaValue,
    GeoShapeValue,
    TabularDataValue,
    MusicalNotationValue,
    URLValue,
    MathValue,
    EntitySchemaValue,
)


def parse_value(snak_json: dict[str, Any]) -> EntityValue | StringValue | TimeValue | QuantityValue | GlobeValue | MonolingualValue | ExternalIDValue | CommonsMediaValue | GeoShapeValue | TabularDataValue | MusicalNotationValue | URLValue | MathValue | EntitySchemaValue:
    if snak_json.get("snaktype") != "value":
        raise ValueError(f"Only value snaks are supported, got snaktype: {snak_json.get('snaktype')}")

    datavalue = snak_json.get("datavalue", {})
    datatype = snak_json.get("datatype")
    value_type = datavalue.get("type", datatype)

    if value_type == "wikibase-entityid":
        return parse_entity_value(datavalue)
    elif value_type == "string":
        return StringValue(value=datavalue.get("value", ""))
    elif value_type == "time":
        return parse_time_value(datavalue)
    elif value_type == "quantity":
        return parse_quantity_value(datavalue)
    elif value_type == "globecoordinate":
        return parse_globe_value(datavalue)
    elif value_type == "monolingualtext":
        return parse_monolingual_value(datavalue)
    elif datatype == "external-id":
        return ExternalIDValue(value=datavalue.get("value", ""))
    elif datatype == "commonsMedia":
        return CommonsMediaValue(value=datavalue.get("value", ""))
    elif datatype == "geo-shape":
        return GeoShapeValue(value=datavalue.get("value", ""))
    elif datatype == "tabular-data":
        return TabularDataValue(value=datavalue.get("value", ""))
    elif datatype == "musical-notation":
        return MusicalNotationValue(value=datavalue.get("value", ""))
    elif datatype == "url":
        return URLValue(value=datavalue.get("value", ""))
    elif datatype == "math":
        return MathValue(value=datavalue.get("value", ""))
    elif datatype == "entity-schema":
        return EntitySchemaValue(value=datavalue.get("value", ""))
    else:
        raise ValueError(f"Unsupported value type: {value_type}, datatype: {datatype}")


def parse_entity_value(datavalue: dict[str, Any]) -> EntityValue:
    entity_id = datavalue.get("value", {}).get("id", "")
    return EntityValue(value=entity_id)


def parse_time_value(datavalue: dict[str, Any]) -> TimeValue:
    time_data = datavalue.get("value", {})
    return TimeValue(
        value=time_data.get("time", ""),
        timezone=time_data.get("timezone", 0),
        before=time_data.get("before", 0),
        after=time_data.get("after", 0),
        precision=time_data.get("precision", 11),
        calendarmodel=time_data.get("calendarmodel", "http://www.wikidata.org/entity/Q1985727")
    )


def parse_quantity_value(datavalue: dict[str, Any]) -> QuantityValue:
    quantity_data = datavalue.get("value", {})
    return QuantityValue(
        value=str(quantity_data.get("amount", "0")),
        unit=quantity_data.get("unit", "1"),
        upper_bound=str(quantity_data["upperBound"]) if "upperBound" in quantity_data else None,
        lower_bound=str(quantity_data["lowerBound"]) if "lowerBound" in quantity_data else None
    )


def parse_globe_value(datavalue: dict[str, Any]) -> GlobeValue:
    globe_data = datavalue.get("value", {})
    return GlobeValue(
        value="",
        latitude=float(globe_data.get("latitude", 0.0)),
        longitude=float(globe_data.get("longitude", 0.0)),
        altitude=float(globe_data["altitude"]) if "altitude" in globe_data else None,
        precision=float(globe_data.get("precision", 1 / 3600)),
        globe=globe_data.get("globe", "http://www.wikidata.org/entity/Q2")
    )


def parse_monolingual_value(datavalue: dict[str, Any]) -> MonolingualValue:
    mono_data = datavalue.get("value", {})
    return MonolingualValue(
        value="",
        language=mono_data.get("language", ""),
        text=mono_data.get("text", "")
    )
