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
    logger.debug(f"First 100 chars of input: {repr(ttl[:100])}")

    ttl = re.sub(r"#.*$", "", ttl, flags=re.MULTILINE)
    logger.debug(f"After removing comments: {len(ttl)} chars")

    ttl = re.sub(r"[ \t]+", " ", ttl)
    logger.debug(f"After normalizing whitespace: {len(ttl)} chars")
    logger.debug(f"First 100 chars: {repr(ttl[:100])}")

    ttl = re.sub(r"\n\n+", "\n\n", ttl)
    logger.debug(f"After normalizing newlines: {len(ttl)} chars")
    logger.debug(f"First 100 chars: {repr(ttl[:100])}")

    result = ttl.strip()
    logger.debug(f"Result length: {len(result)} chars")
    logger.debug(f"First 100 chars: {repr(result[:100])}")
    logger.debug(f"=== normalize_ttl() END ===")
    return result


def split_subject_blocks(ttl: str) -> dict[str, str]:
    blocks = {}
    current_subject = None
    current_lines = []

    for line in ttl.splitlines():
        if not line.strip():
            continue

        line_stripped = line.strip()
        if line_stripped.lower().startswith("@prefix"):
            continue

        if line_stripped.startswith("<http") or line_stripped.startswith("<https"):
            continue

        if line and not line.startswith((" ", "\t")):
            if current_subject:
                blocks[current_subject] = "\n".join(current_lines).strip()
            current_subject = line.split()[0]
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_subject:
        blocks[current_subject] = "\n".join(current_lines).strip()

    return blocks


def load_full_property_registry() -> PropertyRegistry:
    """Load property registry from CSV cache"""
    import csv
    import logging

    logger = logging.getLogger(__name__)

    cache_path = TEST_DATA_DIR / "properties" / "properties.csv"

    if not cache_path.exists():
        raise FileNotFoundError(
            f"Property cache not found: {cache_path}\n"
            f"Run: ./scripts/download_properties.sh"
        )

    properties = {}
    with open(cache_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            properties[row["property_id"]] = property_shape(
                row["property_id"], row["datatype"]
            )

    logger.debug(f"Loaded {len(properties)} properties from registry")
    if "P625" in properties:
        logger.debug(f"P625 in registry with shape: {properties['P625']}")

    return PropertyRegistry(properties=properties)


@pytest.fixture
def property_registry() -> PropertyRegistry:
    """Minimal property registry for Q120248304 test"""
    properties = {
        "P31": property_shape(
            "P31",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "instance of"}},
        ),
        "P17": property_shape(
            "P17",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "country"}},
        ),
        "P127": property_shape(
            "P127",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "owned by"}},
        ),
        "P131": property_shape(
            "P131",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "located in"}},
        ),
        "P137": property_shape(
            "P137",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "operator"}},
        ),
        "P912": property_shape(
            "P912",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "sponsor"}},
        ),
        "P248": property_shape(
            "P248",
            "wikibase-item",
            labels={"en": {"language": "en", "value": "stated in"}},
        ),
        "P11840": property_shape(
            "P11840",
            "external-id",
            labels={"en": {"language": "en", "value": "crossref ID"}},
        ),
        "P1810": property_shape(
            "P1810", "string", labels={"en": {"language": "en", "value": "short name"}}
        ),
        "P2561": property_shape(
            "P2561",
            "monolingualtext",
            labels={"en": {"language": "en", "value": "description"}},
        ),
        "P5017": property_shape(
            "P5017",
            "time",
            labels={"en": {"language": "en", "value": "date of official opening"}},
        ),
        "P625": property_shape(
            "P625",
            "globe-coordinate",
            labels={"en": {"language": "en", "value": "coordinate location"}},
        ),
        "P6375": property_shape(
            "P6375",
            "monolingualtext",
            labels={"en": {"language": "en", "value": "street address"}},
        ),
    }
    return PropertyRegistry(properties=properties)


@pytest.fixture(scope="session")
def full_property_registry() -> PropertyRegistry:
    """Full property registry with all properties from CSV cache"""
    return load_full_property_registry()


@pytest.fixture
def entity_cache_path() -> Path:
    """Path to entity JSON cache for referenced entities"""
    return TEST_DATA_DIR / "json" / "entities"
