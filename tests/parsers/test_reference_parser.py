import pytest

from services.shared.parsers import parse_reference


def test_parse_reference_with_novalue():
    """Test parsing reference with novalue snak"""
    reference_json = {
        "snaks": {
            "P2": [
                {
                    "snaktype": "novalue",
                    "property": "P2"
                }
            ]
        }
    }

    reference = parse_reference(reference_json)
    assert len(reference.snaks) == 1
    assert reference.snaks[0].property == "P2"
    assert reference.snaks[0].value.kind == "novalue"


def test_parse_reference_with_somevalue():
    """Test parsing reference with somevalue snak"""
    reference_json = {
        "snaks": {
            "P3": [
                {
                    "snaktype": "somevalue",
                    "property": "P3"
                }
            ]
        }
    }

    reference = parse_reference(reference_json)
    assert len(reference.snaks) == 1
    assert reference.snaks[0].property == "P3"
    assert reference.snaks[0].value.kind == "somevalue"
