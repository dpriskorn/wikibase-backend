import pytest

from rdf.conftest import normalize_ttl, split_subject_blocks, TEST_DATA_DIR


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


def test_normalize_ttl_idempotent():
    """Test that running normalize twice produces the same result"""
    input_ttl = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
wd:Q42 a schema:Thing ."""

    result1 = normalize_ttl(input_ttl)
    result2 = normalize_ttl(result1)

    assert result1 == result2
