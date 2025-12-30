from pathlib import Path
import re
import pytest
import logging

logger = logging.getLogger(__name__)

from models.rdf_builder.property_registry.registry import PropertyRegistry
from models.rdf_builder.ontology.datatypes import property_shape

# Resolve project root:
# tests/rdf/conftest.py → tests/rdf → tests → project root
# PROJECT_ROOT = Path(__file__).resolve().parents[2]

TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data"

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def normalize_ttl(ttl: str) -> str:
    logger.debug("=== normalize_ttl() START ===")
    logger.debug(f"Input length: {len(ttl)} chars")
    
    ttl = re.sub(r"#.*$", "", ttl, flags=re.MULTILINE)
    logger.debug(f"After removing comments: {len(ttl)} chars")
    
    ttl = re.sub(r"[ \t]+", " ", ttl)
    logger.debug(f"After normalizing whitespace: {len(ttl)} chars")
    
    ttl = re.sub(r"\n{3,}", "\n\n", ttl)
    logger.debug(f"After normalizing newlines: {len(ttl)} chars")
    
    result = ttl.strip()
    logger.debug(f"=== normalize_ttl() END ===")
    return result

def split_subject_blocks(ttl: str) -> dict[str, str]:
    logger.debug("=== split_subject_blocks() START ===")
    blocks = {}
    current_subject = None
    current_lines = []
    line_count = 0

    for line in ttl.splitlines():
        line_count += 1
        
        if line_count <= 30:
            logger.debug(f"Line {line_count:3}: '{line[:80]}'")
        
        if not line.strip():
            if line_count <= 30:
                logger.debug(f"  -> Skipping (empty line)")
            continue
        
        line_stripped = line.strip()
        if line_stripped.lower().startswith("@prefix"):
            if line_count <= 30:
                logger.debug(f"  -> Skipping (prefix): '{line[:60]}'")
            continue
        
        if line_stripped.startswith("<http") or line_stripped.startswith("<https"):
            if line_count <= 30:
                logger.debug(f"  -> Skipping (URL): '{line[:60]}'")
            continue
        
        if line and not line.startswith((" ", "\t")):
            if current_subject:
                blocks[current_subject] = "\n".join(current_lines).strip()
                if line_count <= 30:
                    logger.debug(f"  -> Saved block: '{current_subject}' ({len(current_lines)} lines)")
            current_subject = line.split()[0]
            current_lines = [line]
            if line_count <= 30:
                logger.debug(f"  -> New subject: '{current_subject}'")
        else:
            current_lines.append(line)

    if current_subject:
        blocks[current_subject] = "\n".join(current_lines).strip()
        logger.debug(f"  -> Final block: '{current_subject}' ({len(current_lines)} lines)")
    
    logger.debug(f"=== split_subject_blocks() END === {len(blocks)} blocks found")
    logger.debug(f"Subject keys: {list(blocks.keys())}")
    return blocks


@pytest.fixture
def property_registry() -> PropertyRegistry:
    """Minimal property registry for Q120248304 test"""
    properties = {
        "P31": property_shape("P31", "wikibase-item"),
        "P17": property_shape("P17", "wikibase-item"),
        "P127": property_shape("P127", "wikibase-item"),
        "P131": property_shape("P131", "wikibase-item"),
        "P137": property_shape("P137", "wikibase-item"),
        "P912": property_shape("P912", "wikibase-item"),
        "P248": property_shape("P248", "wikibase-item"),
        "P1810": property_shape("P1810", "string"),
        "P11840": property_shape("P11840", "external-id"),
        "P2561": property_shape("P2561", "monolingualtext"),
        "P6375": property_shape("P6375", "monolingualtext"),
        "P5017": property_shape("P5017", "time"),
        "P625": property_shape("P625", "globe-coordinate"),
    }
    return PropertyRegistry(properties=properties)
