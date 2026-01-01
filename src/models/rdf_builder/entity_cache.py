import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def _fetch_entity_metadata_batch(entity_ids: list[str]) -> dict[str, dict]:
    """Fetch labels and descriptions for multiple entities via SPARQL."""
    if not entity_ids:
        return {}

    batch_size = 100
    results = {}

    for i in range(0, len(entity_ids), batch_size):
        batch = entity_ids[i : i + batch_size]
        values_clause = " ".join([f"wd:{eid}" for eid in batch])

        query = f"""
        SELECT ?entity ?label ?description WHERE {{
          VALUES ?entity {{ {values_clause} }} .
          OPTIONAL {{ ?entity rdfs:label ?label . FILTER(LANG(?label) = 'en') }}
          OPTIONAL {{ ?entity schema:description ?description . FILTER(LANG(?description) = 'en') }}
        }}
        """

        try:
            response = requests.post(
                "https://query.wikidata.org/sparql",
                params={"query": query, "format": "json"},
                timeout=60,
                headers={
                    "User-Agent": "WikibaseBackend/1.0 (research@wikibase-backend.org)"
                },
            )
            response.raise_for_status()

            for row in response.json()["results"]["bindings"]:
                entity_uri = row["entity"]["value"]
                entity_id = entity_uri.rsplit("/", 1)[-1]
                label = row.get("label", {}).get("value", "")
                description = row.get("description", {}).get("value", "")

                metadata = {}
                metadata["id"] = entity_id
                if label:
                    metadata["labels"] = {"en": {"language": "en", "value": label}}
                if description:
                    metadata["descriptions"] = {
                        "en": {"language": "en", "value": description}
                    }

                results[entity_id] = metadata

            logger.info(
                f"Fetched metadata for {len(batch)} entities (batch {i//batch_size + 1})"
            )
            time.sleep(2)

        except Exception as e:
            logger.error(f"Failed to fetch batch {i//batch_size + 1}: {e}")
            for entity_id in batch:
                results[entity_id] = None

    return results


def load_entity_metadata_batch(
    entity_ids: list[str], metadata_dir: Path
) -> dict[str, bool]:
    """Fetch and save metadata for multiple entities.

    Args:
        entity_ids: List of entity IDs to fetch metadata for
        metadata_dir: Directory to save metadata files

    Returns:
        Dictionary mapping entity_id to success status (True/False)
    """
    metadata_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    fetched_metadata = _fetch_entity_metadata_batch(entity_ids)

    for entity_id, metadata in fetched_metadata.items():
        if metadata:
            output_path = metadata_dir / f"{entity_id}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved metadata for {entity_id} to {output_path}")
            results[entity_id] = True
        else:
            logger.warning(f"Failed to fetch metadata for {entity_id}")
            results[entity_id] = False

    return results


def load_entity_metadata(entity_id: str, metadata_dir: Path) -> dict:
    """Load entity metadata (labels, descriptions) from disk only."""
    json_path = metadata_dir / f"{entity_id}.json"

    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))

    raise FileNotFoundError(f"Entity {entity_id} not found at {json_path}")
