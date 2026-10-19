"""
fifo.py — First In, First Out (FIFO) cache replacement policy.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Tuple
from cache_analyzer.replacement.base import ReplacementPolicy

if TYPE_CHECKING:
    from cache_analyzer.cache import CacheLine, CacheSet


class FIFOPolicy(ReplacementPolicy):
    """Evicts the cache line that was loaded into the cache earliest (lowest inserted_at)."""

    def __init__(self, **kwargs):
        super().__init__(name="FIFO", **kwargs)

    def select_victim(
        self,
        cache_set: CacheSet,
        **kwargs
    ) -> Tuple[int, CacheLine]:
        """Find the way with minimum inserted_at timestamp."""
        best_idx = 0
        min_insert = float("inf")
        for idx, line in enumerate(cache_set.ways):
            if line.inserted_at < min_insert:
                min_insert = line.inserted_at
                best_idx = idx
        return best_idx, cache_set.ways[best_idx]
