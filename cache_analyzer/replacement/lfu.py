"""
lfu.py — Least Frequently Used (LFU) cache replacement policy.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Tuple
from cache_analyzer.replacement.base import ReplacementPolicy

if TYPE_CHECKING:
    from cache_analyzer.cache import CacheLine, CacheSet


class LFUPolicy(ReplacementPolicy):
    """Evicts the cache line accessed the fewest times while resident.
    
    Ties are broken using FIFO (earliest inserted_at) or LRU (oldest last_access).
    """

    def __init__(self, tie_breaker: str = "fifo", **kwargs):
        super().__init__(name="LFU", **kwargs)
        self.tie_breaker = tie_breaker.lower()

    def select_victim(
        self,
        cache_set: CacheSet,
        **kwargs
    ) -> Tuple[int, CacheLine]:
        """Find line with minimum access_count, breaking ties according to configuration."""
        best_idx = 0
        min_count = float("inf")
        min_secondary = float("inf")

        for idx, line in enumerate(cache_set.ways):
            secondary = line.inserted_at if self.tie_breaker == "fifo" else line.last_access
            if (line.access_count < min_count) or (
                line.access_count == min_count and secondary < min_secondary
            ):
                min_count = line.access_count
                min_secondary = secondary
                best_idx = idx

        return best_idx, cache_set.ways[best_idx]
