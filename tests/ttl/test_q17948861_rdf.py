import os

import requests
from rdflib import Graph


def test_q17948861_rdf_compatibility(api_client: requests.Session, base_url: str) -> None:
    """Test entity-api Turtle output against Q17948861 reference"""

    entity_data = {
        "id": "Q17948861",
        "type": "item",
        "labels": {
            "it": {"language": "it", "value": "Olimpiadi invernali 2006/Medagliere"}
        },
        "descriptions": {
            "ryu": {"language": "ryu", "value": "ヰキニュースぬ記事"}
        },
        "aliases": {},
        "claims": {
            "P31": [{
                "mainsnak": {
                    "snaktype": "value",
                    "property": "P31",
                    "hash": "9216fd504c93db4211df818e5f5ea29115b240c1",
                    "datavalue": {
                        "value": {
                            "entity-type": "item",
                            "numeric-id": 17633526,
                            "id": "Q17633526"
                        },
                        "type": "wikibase-entityid"
                    },
                    "datatype": "wikibase-item"
                },
                "type": "statement",
                "id": "Q17948861$FA20AC3A-5627-4EC5-93CA-24F0F00C8AA6",
                "rank": "normal"
            }]
        },
        "sitelinks": {
            "itwikinews": {
                "site": "itwikinews",
                "title": "Olimpiadi invernali 2006/Medagliere",
                "badges": [],
                "url": "https://it.wikinews.org/wiki/Olimpiadi_invernali_2006/Medagliere"
            }
        }
    }

    create_response = api_client.post(f"{base_url}/entity", json=entity_data)
    assert create_response.status_code == 200, f"Failed to create entity: {create_response.status_code}"

    api_response = api_client.get(f"{base_url}/wiki/Special:EntityData/Q17948861.ttl", timeout=5)
    assert api_response.status_code == 200, f"Failed to fetch from API: HTTP {api_response.status_code}"

    g_api = Graph().parse(data=api_response.text, format="turtle")
    
    reference_turtle_path = os.path.join(
        os.path.dirname(__file__),
        "../..",
        "test_data",
        "wikibase",
        "Q17948861.ttl"
    )

    try:
        with open(reference_turtle_path) as f:
            reference_turtle = f.read()
        g_ref = Graph().parse(data=reference_turtle, format="turtle")
    except Exception as e:
        assert False, f"Failed to load reference: {e}"

    api_triples = set(g_api)
    ref_triples = set(g_ref)

    print(f"\n📊 Comparison Results:")
    print(f"   API triples: {len(api_triples)}")
    print(f"   Reference triples: {len(ref_triples)}")
    print(f"   Common: {len(api_triples & ref_triples)}")
    print(f"   API only: {len(api_triples - ref_triples)}")
    print(f"   Reference only: {len(ref_triples - api_triples)}")

    api_only = sorted(api_triples - ref_triples)
    ref_only = sorted(ref_triples - api_triples)

    if api_only:
        print("\n🔴 API-only triples (should not exist):")
        for i, triple in enumerate(api_only, 1):
            print(f"  {i}. {triple}")

    if ref_only:
        print("\n🟢 Reference-only triples (API missing):")
        for i, triple in enumerate(ref_only, 1):
            print(f"  {i}. {triple}")

    print("\n📝 Full API Turtle output:")
    print(api_response.text)

    api_prefixes = set(str(p) for p in g_api.namespaces())
    ref_prefixes = set(str(p) for p in g_ref.namespaces())
    print(f"\n🔍 Prefixes match: {api_prefixes == ref_prefixes}")
    print(f"  API only: {api_prefixes - ref_prefixes}")
    print(f"  Reference only: {ref_prefixes - api_prefixes}")

    api_subjects = set([str(s) for s in g_api.subjects()])
    ref_subjects = set([str(s) for s in g_ref.subjects()])
    print(f"\n🎯 Subjects match: {api_subjects == ref_subjects}")
    print(f"  API only: {sorted(api_subjects - ref_subjects)}")
    print(f"  Reference only: {sorted(ref_subjects - api_subjects)}")

    assert len(api_triples) == len(ref_triples), f"Triple count mismatch: API has {len(api_triples)}, reference has {len(ref_triples)}"
    
    non_blank_api = {str(s) for s in g_api.subjects() if type(s).__name__ != 'BNode'}
    non_blank_ref = {str(s) for s in g_ref.subjects() if type(s).__name__ != 'BNode'}
    
    assert non_blank_api == non_blank_ref, f"Non-blank subjects don't match between API and reference\nAPI only: {sorted(non_blank_api - non_blank_ref)}\nReference only: {sorted(non_blank_ref - non_blank_api)}"
    print("\n✅ TEST PASSED: RDF output matches reference")
