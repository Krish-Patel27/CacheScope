"""
random_policy.py — Random cache replacement policy.
"""

from __future__ import annotations
import random
from typing import TYPE_CHECKING, Optional, Tuple
from cache_analyzer.replacement.base import ReplacementPolicy

if TYPE_CHECKING:
    from cache_analyzer.cache import CacheLine, CacheSet


class RandomPolicy(ReplacementPolicy):
    """Evicts a pseudorandomly chosen way from the set."""

    def __init__(self, seed: Optional[int] = None, **kwargs):
        super().__init__(name="RANDOM", **kwargs)
        self.seed = seed
        self._rng = random.Random(seed)

    def select_victim(
        self,
        cache_set: CacheSet,
        **kwargs
    ) -> Tuple[int, CacheLine]:
        """Randomly pick an active way."""
        victim_idx = self._rng.randint(0, len(cache_set.ways) - 1)
        return victim_idx, cache_set.ways[victim_idx]

    def reset(self):
        """Reset RNG state if seed was provided."""
        if self.seed is not None:
            self._rng.seed(self.seed)
