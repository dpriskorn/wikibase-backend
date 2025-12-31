import hashlib
from typing import Any


def generate_value_node_uri(value: Any, property_id: str) -> str:
    """
    Generate wdv: URI for structured values using MD5 hash.
    
    The hash is based on the serialized value representation.
    This ensures consistent URIs for identical values across entities.
    
    Args:
        value: The value object (TimeValue, QuantityValue, etc.)
        property_id: Property ID for context (e.g., "P569")
    
    Returns:
        Value node ID (e.g., "cd6dd2e48a93286891b0753a1110ac0a")
    
    Examples:
        >>> time_val = TimeValue(value="+1964-05-15T00:00:00Z", precision=11)
        >>> generate_value_node_uri(time_val, "P569")
        'cd6dd2e48a93286891b0753a1110ac0a'
    """
    value_str = _serialize_value(value)
    hash_input = f"{property_id}:{value_str}".encode("utf-8")
    return hashlib.md5(hash_input).hexdigest()


def _serialize_value(value: Any) -> str:
    """
    Serialize value object to string for hashing.
    
    Different value types have different serialization formats.
    """
    if hasattr(value, "kind"):
        kind = value.kind

        if kind == "time":
            return f"t:{value.value}:{value.precision}:{value.timezone}:{value.calendarmodel}"

        elif kind == "quantity":
            parts = [f"q:{value.value}:{value.unit}"]
            if value.upper_bound:
                parts.append(value.upper_bound)
            if value.lower_bound:
                parts.append(value.lower_bound)
            return ":".join(parts)

        elif kind == "globe":
            return f"g:{value.latitude}:{value.longitude}:{value.precision}:{value.globe}"

    return str(value)
