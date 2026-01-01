"""Hash-based deduplication cache for value nodes.

Implements MediaWiki's HashDedupeBag pattern to avoid duplicate value node blocks.
Follows same algorithm as mediawiki-extensions-Wikibase/repo/includes/Rdf/HashDedupeBag.php
"""

from typing import Protocol


class DedupeBag(Protocol):
    """Interface for hash-based deduplication."""

    def already_seen(self, hash: str, namespace: str = "") -> bool:
        """Check if hash+namespace seen before.

        False negatives are acceptable (may return False even if seen before).
        False positives are NOT acceptable (must never return True if not seen before).

        Args:
            hash: Full hash string to check
            namespace: Optional namespace for compartmentalized tracking

        Returns:
            True if definitely seen before, False if maybe not seen
        """
        ...


class HashDedupeBag:
    """Hash-based deduplication with lossy cache (like MediaWiki).

    This implementation operates like a rather lossy cache; it's implemented
    as a hash that just evicts old values when a collision occurs.

    The idea for this implementation was taken mainly from from blog posts:
    - "The Invertible Bloom Filter" by Mike James
      http://www.i-programmer.info/programming/theory/4641-the-invertible-bloom-filter.html
    - "The Opposite of a Bloom Filter" by Jeff Hodges
      http://www.somethingsimilar.com/2012/05/21/the-opposite-of-a-bloom-filter/

    The implementation of alreadySeen() works as follows:

    - Determine $key be truncating the $hash parameter, and prepending the $namespace to it. The
      point of truncation is governed by the $cutoff setting in the parameter, and is used to
      govern the tradeoff between bag size and the likelihood of false negatives.

    - Look up $key in $this->bag. If $this->bag[$key] is not set, return false, indicating that the
      value (combination of $hash and $namespace) has never been seen before (we are sure in this case).

    - If $this->bag[$key] is set, compare the value stored there with $hash. If they are the same,
      return true, to indicate that the value has been seen before.

    - If $hash is different from $this->bag[$key], the value might have been seen before but
      been evicted due to a collision, or not. In this case, return false, to be sure.
      This is safe since the contract of alreadySeen() states that false negatives are admissible.

    - In all cases, before returning anything, set $this->bag[$key] = $hash.

    @license GPL-2.0-or-later
    @author Daniel Kinzler
    """

    def __init__(self, cutoff: int = 5):
        """Initialize HashDedupeBag with the given cutoff value, which is the
        number of hash characters to use. A larger number means less collisions
        (fewer false negatives), but a larger bag. The number can be read as an
        exponent to the size of the hash's alphabet, so with a hex hash and $cutoff = 5,
        you'd get a max bag size of 16^5, and a collision probability of 16^-5 = 1/32.

        @param int $cutoff
            The number of hash characters to use as key.
        """
        if cutoff <= 0:
            raise ValueError(f"cutoff must be positive, got {cutoff}")

        self.bag: dict[str, str] = {}
        self.cutoff = cutoff
        self._hits = 0
        self._misses = 0

    def already_seen(self, hash: str, namespace: str = "") -> bool:
        """
        @see DedupeBag::alreadySeen
        @return bool
        """
        key = namespace + hash[: self.cutoff]

        if key in self.bag and self.bag[key] == hash:
            self._hits += 1
            return True

        self._misses += 1
        self.bag[key] = hash
        return False

    def stats(self) -> dict[str, int | float]:
        """Get deduplication statistics.

        Returns:
            Dict with 'hits', 'misses', 'size', 'collision_rate'
        """
        total = self._hits + self._misses
        collision_rate = (self._misses / total * 100) if total > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self.bag),
            "collision_rate": collision_rate,
        }

    def clear(self):
        """Clears deduplication cache."""
        self.bag.clear()
        self._hits = 0
        self._misses = 0
