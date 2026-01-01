"""Unit tests for HashDedupeBag deduplication cache."""

import pytest
from models.rdf_builder.hashing.deduplication_cache import HashDedupeBag


def test_basic_deduplication():
    """Test that same hash returns True on second call."""
    dedupe = HashDedupeBag()
    assert not dedupe.already_seen("abc123def456", "wdv")
    assert dedupe.already_seen("abc123def456", "wdv") is True


def test_different_hashes():
    """Test that different hashes return False each time."""
    dedupe = HashDedupeBag()
    assert not dedupe.already_seen("abc123def456", "wdv")
    assert not dedupe.already_seen("def456abc123", "wdv")
    assert not dedupe.already_seen("ghj789klm012", "wdv")


def test_namespace_separation():
    """Test that same hash in different namespaces is treated separately."""
    dedupe = HashDedupeBag()
    assert not dedupe.already_seen("abc123def456", "wdv")
    assert dedupe.already_seen("abc123def456", "wdv") is True
    assert not dedupe.already_seen("abc123def456", "stmt")  # Different namespace
    assert dedupe.already_seen("abc123def456", "stmt") is True


def test_cutoff_collision_false_negative():
    """Test that hash collisions cause false negatives (acceptable behavior)."""
    dedupe = HashDedupeBag(cutoff=2)  # Small cutoff to force collisions

    # Different hashes with same first 2 chars will collide
    hash1 = "ab1234567890abcdef1234567890ab"
    hash2 = "ab9876543210fedcba0987654321ba"

    assert not dedupe.already_seen(hash1, "wdv")

    # Verify hash1 is tracked before testing collision
    assert dedupe.already_seen(hash1, "wdv") is True

    # hash2 collides with hash1 (same prefix), so returns False (false negative)
    # This is acceptable per MediaWiki design
    assert not dedupe.already_seen(hash2, "wdv")


def test_stats_tracking():
    """Test that deduplication statistics are tracked correctly."""
    dedupe = HashDedupeBag()

    dedupe.already_seen("abc123", "wdv")
    dedupe.already_seen("abc123", "wdv")
    dedupe.already_seen("def456", "wdv")
    dedupe.already_seen("def456", "wdv")
    dedupe.already_seen("ghi789", "wdv")

    stats = dedupe.stats()
    assert stats["hits"] == 2  # abc123 and def456 seen twice
    assert stats["misses"] == 3  # All three hashes added once
    assert stats["size"] == 3  # Three unique hashes in bag
    assert stats["collision_rate"] == 60.0  # 3 misses / 5 total = 60%


def test_clear():
    """Test that cache can be cleared."""
    dedupe = HashDedupeBag()

    dedupe.already_seen("abc123", "wdv")
    dedupe.already_seen("abc123", "wdv")
    assert dedupe.stats()["size"] == 1

    dedupe.clear()
    assert dedupe.stats()["size"] == 0

    # After clear, same hash is treated as new
    assert not dedupe.already_seen("abc123", "wdv")
    assert dedupe.already_seen("abc123", "wdv") is True


def test_default_cutoff():
    """Test that default cutoff of 5 is used."""
    dedupe = HashDedupeBag()
    assert dedupe.cutoff == 5


def test_custom_cutoff():
    """Test that custom cutoff value is used."""
    dedupe = HashDedupeBag(cutoff=10)
    assert dedupe.cutoff == 10


def test_invalid_cutoff():
    """Test that invalid cutoff values raise ValueError."""
    with pytest.raises(ValueError):
        HashDedupeBag(cutoff=0)

    with pytest.raises(ValueError):
        HashDedupeBag(cutoff=-1)


def test_empty_namespace():
    """Test that empty namespace string works correctly."""
    dedupe = HashDedupeBag()

    assert not dedupe.already_seen("abc123", "")
    assert dedupe.already_seen("abc123", "") is True


def test_long_hash_truncation():
    """Test that long hashes are properly truncated for key."""
    dedupe = HashDedupeBag(cutoff=3)

    # Same first 3 chars, different rest
    hash1 = "abc" + "123" * 10
    hash2 = "abc" + "456" * 10

    assert not dedupe.already_seen(hash1, "wdv")
    assert dedupe.already_seen(hash1, "wdv") is True  # Verify hash1 tracked
    assert not dedupe.already_seen(hash2, "wdv")  # Collides


def test_hash_preservation():
    """Test that full hash is preserved in bag, not truncated."""
    dedupe = HashDedupeBag(cutoff=3)

    full_hash = "abcdefghijklmnopqrstuvwxyz123456"
    assert not dedupe.already_seen(full_hash, "wdv")

    # Bag should contain full hash, not just prefix
    key = "wdv" + full_hash[:3]
    assert dedupe.bag[key] == full_hash


def test_multiple_namespaces():
    """Test tracking across multiple namespaces."""
    dedupe = HashDedupeBag()

    assert not dedupe.already_seen("abc123", "wdv")
    assert not dedupe.already_seen("abc123", "stmt")
    assert not dedupe.already_seen("abc123", "qual")

    # Each namespace tracked separately
    assert dedupe.already_seen("abc123", "wdv") is True
    assert dedupe.already_seen("abc123", "stmt") is True
    assert dedupe.already_seen("abc123", "qual") is True

    stats = dedupe.stats()
    assert stats["size"] == 3  # Three entries (one per namespace)
