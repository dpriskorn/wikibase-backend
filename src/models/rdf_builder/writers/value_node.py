from typing import TextIO
import re

from models.rdf_builder.uri_generator import URIGenerator
from models.rdf_builder.hashing.deduplication_cache import HashDedupeBag


def _format_scientific_notation(value: float) -> str:
    """Format value in scientific notation without leading zeros in exponent.

    Converts Python's 1.0E-05 format to Wikidata's 1.0E-5 format.

    Args:
        value: Numeric value to format

    Returns:
        String in scientific notation (e.g., "1.0E-5")
    """
    formatted = f"{value:.1E}"
    match = re.match(r"([+-]?[0-9.]+E)([+-])0([0-9]+)$", formatted)
    if match:
        mantissa = match.group(1)
        sign = match.group(2)
        exponent = match.group(3)
        return f"{mantissa}{sign}{exponent}"
    return formatted


class ValueNodeWriter:
    """Write structured value nodes (wdv:) for time, quantity, globe-coordinate"""

    uri = URIGenerator()

    @staticmethod
    def write_time_value_node(
        output: TextIO, value_id: str, time_value, dedupe: HashDedupeBag | None = None
    ):
        """Write time value node block if not already written"""
        if dedupe is not None:
            if dedupe.already_seen(value_id, "wdv"):
                return

        time_str = time_value.value
        if time_value.timezone == 0 and time_str.startswith("+"):
            time_str = time_str[1:]  # Remove leading + for timezone 0
        output.write(f"wdv:{value_id} a wikibase:TimeValue ;\n")
        output.write(f'\twikibase:timeValue "{time_str}"^^xsd:dateTime ;\n')
        output.write(
            f'\twikibase:timePrecision "{time_value.precision}"^^xsd:integer ;\n'
        )
        output.write(
            f'\twikibase:timeTimezone "{time_value.timezone}"^^xsd:integer ;\n'
        )
        output.write(f"\twikibase:timeCalendarModel <{time_value.calendarmodel}> .\n")

    @staticmethod
    def write_quantity_value_node(
        output: TextIO,
        value_id: str,
        quantity_value,
        dedupe: HashDedupeBag | None = None,
    ):
        """Write quantity value node block if not already written"""
        if dedupe is not None:
            if dedupe.already_seen(value_id, "wdv"):
                return

        output.write(f"wdv:{value_id} a wikibase:QuantityValue ;\n")
        output.write(
            f'\twikibase:quantityAmount "{quantity_value.value}"^^xsd:decimal ;\n'
        )
        output.write(f"\twikibase:quantityUnit <{quantity_value.unit}>")

        if quantity_value.upper_bound:
            output.write(f" ;\n")
            output.write(
                f'\twikibase:quantityUpperBound "{quantity_value.upper_bound}"^^xsd:decimal'
            )

        if quantity_value.lower_bound:
            if not quantity_value.upper_bound:
                output.write(f" ;\n")
            output.write(
                f'\twikibase:quantityLowerBound "{quantity_value.lower_bound}"^^xsd:decimal'
            )

        output.write(f" .\n")

    @staticmethod
    def write_globe_value_node(
        output: TextIO, value_id: str, globe_value, dedupe: HashDedupeBag | None = None
    ):
        """Write globe coordinate value node block if not already written"""
        if dedupe is not None:
            if dedupe.already_seen(value_id, "wdv"):
                return

        precision_formatted = _format_scientific_notation(globe_value.precision)
        output.write(f"wdv:{value_id} a wikibase:GlobecoordinateValue ;\n")
        output.write(f'\twikibase:geoLatitude "{globe_value.latitude}"^^xsd:double ;\n')
        output.write(
            f'\twikibase:geoLongitude "{globe_value.longitude}"^^xsd:double ;\n'
        )
        output.write(f'\twikibase:geoPrecision "{precision_formatted}"^^xsd:double ;\n')
        output.write(f"\twikibase:geoGlobe <{globe_value.globe}> .\n")
