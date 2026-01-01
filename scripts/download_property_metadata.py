#!/usr/bin/env python3
"""
Download property metadata from Wikidata SPARQL endpoint.

Fetches labels and descriptions for all properties in properties.csv.
Saves each property as individual JSON file: test_data/properties/{Pxxx}.json

Usage:
    python scripts/download_property_metadata.py
"""

import csv
import sys
import time
from pathlib import Path

import requests

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"


def fetch_property_metadata(properties_csv: Path, output_dir: Path) -> None:
    """
    Fetch metadata for all properties from CSV via SPARQL.

    Args:
        properties_csv: Path to properties.csv file
        output_dir: Directory to save property JSON files
    """
    # Read all property IDs from CSV
    property_ids = []
    with open(properties_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            property_ids.append(row["property_id"])

    print(f"Found {len(property_ids)} properties in CSV")
    print(f"First 5 properties: {property_ids[:5]}")

    # Filter out properties that already exist
    existing_properties = set()
    for json_file in output_dir.glob("*.json"):
        existing_properties.add(json_file.stem)

    property_ids_to_download = [
        pid for pid in property_ids if pid not in existing_properties
    ]

    if len(property_ids_to_download) < len(property_ids):
        print(
            f"Skipping {len(property_ids) - len(property_ids_to_download)} already downloaded"
        )
    print(f"Need to download {len(property_ids_to_download)} properties")

    # Build SPARQL query for all properties
    # Using smaller batches (100) for reliability
    batch_size = 100
    total_downloaded = 0

    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(0, len(property_ids_to_download), batch_size):
        batch = property_ids_to_download[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(property_ids_to_download) + batch_size - 1) // batch_size

        print(
            f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} properties)..."
        )

        # Build VALUES clause for SPARQL
        values_clause = " ".join([f"wd:{pid}" for pid in batch])

        query = f"""
        SELECT ?property ?label ?description WHERE {{
          VALUES ?property {{ {values_clause} }} .
          ?property a wikibase:Property .
          OPTIONAL {{ ?property rdfs:label ?label . FILTER(LANG(?label) = 'en') }}
          OPTIONAL {{ ?property schema:description ?description . FILTER(LANG(?description) = 'en') }}
        }}
        """

        response = None

        try:
            print(f"  Querying SPARQL endpoint using POST...")

            response = requests.post(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                timeout=60,
                headers={
                    "User-Agent": "WikibaseBackend/1.0 (research@wikibase-backend.org)"
                },
            )
            print(f"  Response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            results = data["results"]["bindings"]

            print(f"  Got {len(results)} results")

            # Save each property as JSON
            for result in results:
                prop_uri = result["property"]["value"]
                property_id = prop_uri.rsplit("/", 1)[-1]

                label = result.get("label", {}).get("value", "")
                description = result.get("description", {}).get("value", "")

                # Build labels dict
                labels_dict = (
                    {"en": {"language": "en", "value": label}} if label else {}
                )

                # Build descriptions dict
                descriptions_dict = (
                    {"en": {"language": "en", "value": description}}
                    if description
                    else {}
                )

                property_data = {
                    "id": property_id,
                    "labels": labels_dict,
                    "descriptions": descriptions_dict,
                }

                output_path = output_dir / f"{property_id}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    import json as json2

                    json2.dump(property_data, f, indent=2)

                total_downloaded += 1

            print(f"  Saved {len(results)} property JSON files")

            # Rate limiting: avoid hitting SPARQL endpoint too hard
            time.sleep(2)

        except Exception as e:
            print(f"  ❌ Error in batch {batch_num}: {e}")
            if "response" in locals() and hasattr(response, "text"):
                print(f"  Response content: {response.text[:500]}")
            import traceback

            traceback.print_exc()
            continue

    print(f"\n✅ Done! Downloaded {total_downloaded} property metadata files")
    print(f"   Output directory: {output_dir}")

    if total_downloaded == 0:
        print("\n⚠️  WARNING: No files were downloaded!")
        print(f"   Check if properties.csv exists and is not empty")
        print(f"   Path: {properties_csv}")


def main():
    """Main function"""
    # Paths
    project_root = Path(__file__).parent.parent
    properties_csv = project_root / "test_data" / "properties" / "properties.csv"
    output_dir = project_root / "test_data" / "properties"

    if not properties_csv.exists():
        print(f"❌ Properties CSV not found: {properties_csv}")
        print(f"Run: ./scripts/download_properties.sh")
        sys.exit(1)

    print(f"Loading properties from: {properties_csv}")
    print(f"Saving to: {output_dir}")

    # Fetch metadata
    fetch_property_metadata(properties_csv, output_dir)


if __name__ == "__main__":
    main()
