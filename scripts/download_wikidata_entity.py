#!/usr/bin/env python3
"""
Download Wikidata entity data (JSON and TTL) for testing.

Usage:
    python scripts/download_wikidata_entity.py Q42
    python scripts/download_wikidata_entity.py Q42 Q17948861
"""

import sys
import json
import requests
from pathlib import Path


def download_entity_json(entity_id: str, output_dir: Path) -> None:
    """Download entity JSON from Wikidata"""
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
    
    headers = {
        "User-Agent": "WikibaseBackend/1.0 (research@wikibase-backend.org)"
    }
    
    print(f"Downloading {entity_id}.json from {url}...")
    response = requests.get(url, timeout=30, headers=headers)
    response.raise_for_status()
    
    output_path = output_dir / f"{entity_id}.json"
    with open(output_path, 'w') as f:
        json.dump(response.json(), f, indent=2)
    
    print(f"Saved to {output_path}")


def download_entity_ttl(entity_id: str, output_dir: Path) -> None:
    """Download entity TTL from Wikidata"""
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.ttl"
    
    headers = {
        "User-Agent": "WikibaseBackend/1.0 (research@wikibase-backend.org)"
    }
    
    print(f"Downloading {entity_id}.ttl from {url}...")
    response = requests.get(url, timeout=30, headers=headers)
    response.raise_for_status()
    
    output_path = output_dir / f"{entity_id}.ttl"
    with open(output_path, 'w') as f:
        f.write(response.text)
    
    print(f"Saved to {output_path}")


def download_entity(entity_id: str) -> None:
    """Download both JSON and TTL for an entity"""
    json_output_dir = Path(__file__).parent.parent / "test_data" / "json" / "entities"
    json_output_dir.mkdir(parents=True, exist_ok=True)
    ttl_output_dir = Path(__file__).parent.parent / "test_data" / "rdf" / "ttl"
    ttl_output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading data for {entity_id}...")

    download_entity_json(entity_id, json_output_dir)
    download_entity_ttl(entity_id, ttl_output_dir)
    
    print(f"\n✅ Downloaded both {entity_id}.json and {entity_id}.ttl")


def main():
    if len(sys.argv) < 2:
        print("Usage: python download_wikidata_entity.py <entity_id> [entity_id2] ...")
        print("Example: python download_wikidata_entity.py Q42")
        print("         python download_wikidata_entity.py Q42 Q17948861")
        sys.exit(1)
    
    entity_ids = sys.argv[1:]
    
    for entity_id in entity_ids:
        try:
            download_entity(entity_id)
        except Exception as e:
            print(f"\n❌ Error downloading {entity_id}: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
