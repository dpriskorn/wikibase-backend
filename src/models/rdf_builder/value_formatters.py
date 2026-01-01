import logging
from typing import Any
from models.internal_representation.value_kinds import ValueKind

logger = logging.getLogger(__name__)


class ValueFormatter:
    """Format internal Value objects as RDF literals/URIs"""

    @staticmethod
    def format_value(value: Any) -> str:
        """Format a Value object as RDF string"""
        kind = value.kind

        if kind == ValueKind.ENTITY:
            return f"wd:{value.value}"

        elif kind == ValueKind.STRING:
            escaped = ValueFormatter.escape_turtle(value.value)
            return f'"{escaped}"'

        elif kind == ValueKind.TIME:
            return f'"{value.value}"^^xsd:dateTime'

        elif kind == ValueKind.QUANTITY:
            return f"{value.value}^^xsd:decimal"

        elif kind == ValueKind.GLOBE:
            coord = f"Point({value.longitude} {value.latitude})"
            formatted = f'"{coord}"^^geo:wktLiteral'
            logger.debug(
                f"GLOBE value formatting: lat={value.latitude}, lon={value.longitude} -> {formatted}"
            )
            return formatted

        elif kind == ValueKind.MONOLINGUAL:
            escaped = ValueFormatter.escape_turtle(value.text)
            return f'"{escaped}"@{value.language}'

        elif kind == ValueKind.EXTERNAL_ID:
            escaped = ValueFormatter.escape_turtle(value.value)
            return f'"{escaped}"'

        elif kind == ValueKind.COMMONS_MEDIA:
            file = ValueFormatter.escape_turtle(value.value)
            return f'"{file}"'

        elif kind == ValueKind.GEO_SHAPE:
            shape = ValueFormatter.escape_turtle(value.value)
            return f'"{shape}"'

        elif kind == ValueKind.URL:
            url = ValueFormatter.escape_turtle(value.value)
            return f'"{url}"'

        elif kind == ValueKind.NOVALUE:
            return "wikibase:noValue"

        elif kind == ValueKind.SOMEVALUE:
            return "wikibase:someValue"

        else:
            return ""

    @staticmethod
    def escape_turtle(value: str) -> str:
        """Escape special characters for Turtle format"""
        value = value.replace("\\", "\\\\")
        value = value.replace('"', '\\"')
        value = value.replace("\n", "\\n")
        value = value.replace("\r", "\\r")
        value = value.replace("\t", "\\t")
        return value
