import hashlib
import re
from typing import Any


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


def generate_value_node_uri(value: Any) -> str:
    """
    Generate wdv: URI for structured values using MD5 hash.

    The hash is based on the serialized value representation only,
    ensuring consistent URIs for identical values across entities,
    properties, and contexts (statements, qualifiers, references).

    Args:
        value: The value object (TimeValue, QuantityValue, GlobeValue)

    Returns:
        Value node ID (e.g., "cd6dd2e48a93286891b0753a1110ac0a")

    Examples:
        >>> time_val = TimeValue(value="+1964-05-15T00:00:00Z", precision=11)
        >>> generate_value_node_uri(time_val)
        'cd6dd2e48a93286891b0753a1110ac0a'
    """
    value_str = _serialize_value(value)
    hash_val = hashlib.md5(value_str.encode("utf-8")).hexdigest()
    return hash_val


def _serialize_value(value: Any) -> str:
    """
    Serialize value object to string for hashing.

    Different value types have different serialization formats.
    """
    if hasattr(value, "kind"):
        kind = value.kind

        if kind == "time":
            time_str = value.value
            if value.timezone == 0 and time_str.startswith("+"):
                time_str = time_str[1:]  # Remove leading + for timezone 0
            parts = [f"t:{time_str}", value.precision, value.timezone]
            if value.before != 0:
                parts.append(value.before)
            if value.after != 0:
                parts.append(value.after)
            parts.append(value.calendarmodel)
            return ":".join(str(p) for p in parts)

        elif kind == "quantity":
            parts = [f"q:{value.value}:{value.unit}"]
            if value.upper_bound:
                parts.append(value.upper_bound)
            if value.lower_bound:
                parts.append(value.lower_bound)
            return ":".join(parts)

        elif kind == "globe":
            precision_formatted = _format_scientific_notation(value.precision)
            return f"g:{value.latitude}:{value.longitude}:{precision_formatted}:{value.globe}"

    return str(value)
