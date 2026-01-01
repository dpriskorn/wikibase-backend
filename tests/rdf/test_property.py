from io import StringIO

from models.internal_representation.property_metadata import (
    PropertyMetadata,
    WikibaseDatatype,
)
from models.rdf_builder.writers.property import PropertyWriter


def test_property_p17_scaffolding():
    prop = PropertyMetadata("P17", WikibaseDatatype.WIKIBASE_ITEM)
    out = StringIO()
    PropertyWriter.write_property(out, prop)

    ttl = out.getvalue()
    assert "wikibase:Property" in ttl
    assert "wikibase:directClaim wdt:P17" in ttl
