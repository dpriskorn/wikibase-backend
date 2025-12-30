import pytest

from rdf.conftest import normalize_ttl, TEST_DATA_DIR


def test_normalize_ttl_removes_comments():
    """Test that comments are removed from TTL"""
    input_ttl = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
# This is a comment
wd:Q42 a schema:Thing .
# Another comment"""

    result = normalize_ttl(input_ttl)

    assert "# This is a comment" not in result
    assert "# Another comment" not in result
    assert "@prefix" in result
    assert "wd:Q42" in result


def test_normalize_ttl_normalizes_whitespace():
    """Test that tabs and multiple spaces are normalized to single spaces"""
    input_ttl = "@prefix rdf:\t<http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\nwd:Q42  a  schema:Thing ."

    result = normalize_ttl(input_ttl)

    assert "\t" not in result
    assert "  " not in result
    assert "@prefix rdf: <" in result


def test_normalize_ttl_empty_input():
    """Test that empty input is handled correctly"""
    result = normalize_ttl("")
    assert result == ""


def test_normalize_ttl_normalizes_newlines():
    """Test that multiple consecutive newlines are normalized"""
    input_ttl = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .


wd:Q42 a schema:Thing ."""

    result = normalize_ttl(input_ttl)

    assert "\n\n\n" not in result
    assert "@prefix rdf:" in result
    assert "wd:Q42" in result


def test_normalize_ttl_preserves_rdf_content():
    """Test that normalization preserves RDF content using real TTL file"""
    ttl_path = TEST_DATA_DIR / "rdf" / "ttl" / "Q17948861.ttl"
    input_ttl = ttl_path.read_text(encoding="utf-8")

    result = normalize_ttl(input_ttl)

    assert "@prefix" in result
    assert "wd:Q17948861" in result
    assert "schema:Dataset" in result
    assert "wikibase:Item" in result
    assert len(result) > 0


def test_normalize_ttl_strips_edges():
    """Test that leading and trailing whitespace is removed"""
    input_ttl = """   \n@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
wd:Q42 a schema:Thing .\n   """

    result = normalize_ttl(input_ttl)

    assert not result.startswith(" ")
    assert not result.startswith("\n")
    assert not result.endswith(" ")
    assert not result.endswith("\n")
    assert "@prefix rdf:" in result


def test_normalize_ttl_idempotent():
    """Test that running normalize twice produces the same result"""
    input_ttl = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
wd:Q42 a schema:Thing ."""

    result1 = normalize_ttl(input_ttl)
    result2 = normalize_ttl(result1)

    assert result1 == result2


def test_q17948861_load_and_normalize():
    """Test loading and normalizing Q17948861 files"""
    entity_id = "Q17948861"

    json_path = TEST_DATA_DIR / "json" / "entities" / f"{entity_id}.json"
    ttl_path = TEST_DATA_DIR / "rdf" / "ttl" / f"{entity_id}.ttl"

    assert json_path.exists(), f"JSON file not found: {json_path}"
    assert ttl_path.exists(), f"TTL file not found: {ttl_path}"

    json_text = json_path.read_text(encoding="utf-8")
    ttl_text = ttl_path.read_text(encoding="utf-8")

    normalized_ttl = normalize_ttl(ttl_text)

    assert len(json_text) > 0
    assert len(ttl_text) > 0
    assert len(normalized_ttl) > 0
    assert "wd:Q17948861" in normalized_ttl
