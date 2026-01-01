#!/usr/bin/env python3
"""
Download all Wikidata property datatypes via SPARQL and save to CSV.

Usage:
    python scripts/download_properties_sparql.py
"""

import csv
import sys
from pathlib import Path

import requests

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"


def main() -> None:
    """Download all properties and save to CSV"""
    # Query to get all properties with their datatypes
    query = """
    SELECT ?property ?datatype WHERE {
      ?property a wikibase:Property .
      ?property wikibase:propertyType ?datatype .
    }
    """

    print("Fetching properties from SPARQL endpoint...")

    response = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        timeout=60,
        headers={"User-Agent": "WikibaseBackend/1.0 (research@wikibase-backend.org)"},
    )
    response.raise_for_status()

    data = response.json()
    properties = data["results"]["bindings"]

    print(f"Got {len(properties)} properties")

    # Determine output path
    output_path = (
        Path(__file__).parent.parent / "test_data" / "properties" / "properties.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["property_id", "datatype"])

        for prop in properties:
            # Extract property ID from URI: http://www.wikidata.org/entity/P31 -> P31
            prop_uri = prop["property"]["value"]
            property_id = prop_uri.rsplit("/", 1)[-1]

            # Extract datatype fragment from URI: http://wikiba.se/ontology#WikibaseItem -> WikibaseItem
            datatype_uri = prop["datatype"]["value"]
            datatype_name = datatype_uri.rsplit("#", 1)[-1]

            writer.writerow([property_id, datatype_name])

    print(f"✅ Saved to {output_path}")
    print(f"   Total properties: {len(properties)}")


if __name__ == "__main__":
    main()
