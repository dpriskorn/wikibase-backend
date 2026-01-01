"""MediaWiki-compatible value node hash generation."""

import hashlib


class ValueNodeHasher:
    """Generates value node URIs (wdv:) using MediaWiki's hash format.

    Follows MediaWiki Wikibase's approach from Rdf/Values/README.md.
    Hash is computed from internal serialization format, not RDF output.
    """

    @staticmethod
    def _format_precision(value: float) -> str:
        """Format precision to remove leading zero in exponent.

        MediaWiki normalizes precision to remove leading zeros in exponent:
        "1.0E-5" -> "1.0E-5"
        "1.0E-05" -> "1.0E-5"

        Returns value in scientific notation without leading zeros after E.
        """
        formatted = f"{value:.1E}"
        if "E-0" in formatted:
            formatted = formatted.replace("E-0", "E-")
        return formatted

    @staticmethod
    def hash_time_value(
        time_str: str, precision: int, timezone: int, calendar: str
    ) -> str:
        """Hash time value - keeps leading + in hash input (removed in output)."""
        # Leading + is part of MediaWiki's hash input
        # But removed in RDF output when timezone=0
        parts = [f"t:{time_str}", str(precision), str(timezone), calendar]
        return hashlib.md5(":".join(parts).encode()).hexdigest()

    @staticmethod
    def hash_quantity_value(
        value: str,
        unit: str,
        upper_bound: str | None = None,
        lower_bound: str | None = None,
    ) -> str:
        """Hash quantity value."""
        parts = [f"q:{value}:{unit}"]
        if upper_bound is not None:
            parts.append(upper_bound)
        if lower_bound is not None:
            parts.append(lower_bound)
        return hashlib.md5(":".join(parts).encode()).hexdigest()

    @staticmethod
    def hash_entity_value(value: str) -> str:
        """Hash entity value."""
        return hashlib.md5(value.encode()).hexdigest()
