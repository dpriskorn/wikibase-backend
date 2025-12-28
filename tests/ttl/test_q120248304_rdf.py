import os
import json
import requests
from rdflib import Graph


def test_q120248304_rdf_compatibility(api_client: requests.Session, base_url: str) -> None:
    """Test entity-api Turtle output against Q120248304 reference - all triple content must match"""

    with open(os.path.join(
        os.path.dirname(__file__),
        "../..",
        "test_data",
        "wikibase",
        "Q120248304.json"
    )) as f:
        entity_data_raw = json.load(f)
    
    entity_data = entity_data_raw['entities']['Q120248304']

    create_response = api_client.post(f"{base_url}/entity", json=entity_data)
    assert create_response.status_code == 200, f"Failed to create entity: {create_response.status_code}"

    api_response = api_client.get(f"{base_url}/wiki/Special:EntityData/Q120248304.ttl", timeout=5)
    assert api_response.status_code == 200, f"Failed to fetch from API: HTTP {api_response.status_code}"

    reference_turtle_path = os.path.join(
        os.path.dirname(__file__),
        "../..",
        "test_data",
        "wikibase",
        "Q120248304.ttl"
    )

    with open(reference_turtle_path) as f:
        reference_turtle = f.read()

    g_api = Graph().parse(data=api_response.text, format="turtle")
    g_ref = Graph().parse(data=reference_turtle, format="turtle")

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
        print(f"\n🔴 API-only triples ({len(api_only)} total, showing first 10):")
        for i, triple in enumerate(api_only[:10], 1):
            print(f"  {i}. {triple}")
        if len(api_only) > 10:
            print(f"  ... and {len(api_only) - 10} more")

    if ref_only:
        print(f"\n🟢 Reference-only triples ({len(ref_only)} total, showing first 10):")
        for i, triple in enumerate(ref_only[:10], 1):
            print(f"  {i}. {triple}")
        if len(ref_only) > 10:
            print(f"  ... and {len(ref_only) - 10} more")

    assert len(api_triples) == len(ref_triples), f"Triple count mismatch: API has {len(api_triples)}, reference has {len(ref_triples)}"
    assert api_triples == ref_triples, f"Triple content mismatch: {len(api_triples - ref_triples)} triples differ"
    print("\n✅ TEST PASSED: Q120248304 RDF output matches reference")
