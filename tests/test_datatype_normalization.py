"""
Test CamelCase to kebab-case normalization
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from models.internal_representation.datatypes import Datatype


def test_camelcase_to_kebab_normalization():
    """Test CamelCase to kebab-case normalization"""

    # Test Wikibase prefixes
    assert Datatype.normalize_from_sparql("WikibaseItem") == "wikibase-item"
    assert Datatype.normalize_from_sparql("WikibaseString") == "wikibase-string"
    assert (
        Datatype.normalize_from_sparql("WikibaseMonolingualtext")
        == "wikibase-monolingualtext"
    )
    assert Datatype.normalize_from_sparql("WikibaseExternalId") == "external-id"
    assert Datatype.normalize_from_sparql("WikibaseUrl") == "url"
    assert Datatype.normalize_from_sparql("WikibaseProperty") == "wikibase-property"
    assert (
        Datatype.normalize_from_sparql("WikibaseMusicalNotation") == "musical-notation"
    )

    # Test without prefix (variants)
    assert Datatype.normalize_from_sparql("Item") == "item"
    assert Datatype.normalize_from_sparql("String") == "string"
    assert Datatype.normalize_from_sparql("Monolingualtext") == "monolingualtext"
    assert Datatype.normalize_from_sparql("ExternalId") == "external-id"
    assert Datatype.normalize_from_sparql("Url") == "url"
    assert Datatype.normalize_from_sparql("Property") == "property"
    assert Datatype.normalize_from_sparql("MusicalNotation") == "musical-notation"


if __name__ == "__main__":
    test_camelcase_to_kebab_normalization()
    print("✅ All CamelCase normalization tests passed!")
