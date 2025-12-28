"""Test fixtures for RDF serialization tests"""
import json
import os
from pathlib import Path
from typing import Any
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

BASE_DIR = Path(__file__).parent.parent.parent  # Go up to project root
TEST_DATA_DIR = BASE_DIR / "test_data"
EXPECTED_DIR = TEST_DATA_DIR / "expected_rdf"

def load_json_entity(entity_id: str) -> dict[str, Any]:
    """Load JSON entity from test data"""
    entity_file = TEST_DATA_DIR / "entities" / f"{entity_id}.json"
    if not entity_file.exists():
        raise FileNotFoundError(f"Entity file not found: {entity_file}")
    with open(entity_file) as f:
        data = json.load(f)
    # Handle both formats: direct entity dict or wrapped in {"entities": {}}
    if "entities" in data:
        return data["entities"][entity_id]
    return data

def load_expected_rdf(entity_id: str, filename: str) -> str:
    """Load expected RDF from expected directory"""
    # Try to find the file in subdirectories first
    for subdir in ["statements", "values", "qualifiers", "references", "referenced", "terms", "sitelinks", "properties"]:
        expected_file = EXPECTED_DIR / subdir / filename
        if expected_file.exists():
            with open(expected_file) as f:
                return f.read()
    
    # Try direct in expected directory
    expected_file = EXPECTED_DIR / filename
    if expected_file.exists():
        with open(expected_file) as f:
            return f.read()
    
    raise FileNotFoundError(f"Expected RDF file not found: {filename}")

def serialize_entity(entity: dict) -> str:
    """Serialize entity to RDF Turtle format"""
    from services.entity_api.rdf.serializer import serialize_entity_to_turtle
    return serialize_entity_to_turtle(entity, entity.get("id", ""))

def normalize_ntriples(rdf_str: str) -> str:
    """Normalize NTriples for comparison (sort lines, normalize whitespace)"""
    lines = rdf_str.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    lines.sort()
    return '\n'.join(lines)

def normalize_turtle(rdf_str: str) -> str:
    """Normalize Turtle for comparison (sort triples, normalize whitespace)"""
    lines = rdf_str.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    # Simple line-based sorting (not perfect but good enough)
    lines.sort()
    return '\n'.join(lines)
