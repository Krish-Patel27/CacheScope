"""
lru.py — Least Recently Used (LRU) cache replacement policy.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Tuple
from cache_analyzer.replacement.base import ReplacementPolicy

if TYPE_CHECKING:
    from cache_analyzer.cache import CacheLine, CacheSet


class LRUPolicy(ReplacementPolicy):
    """Evicts the cache line whose last access timestamp is lowest (oldest)."""

    def __init__(self, **kwargs):
        super().__init__(name="LRU", **kwargs)

    def select_victim(
        self,
        cache_set: CacheSet,
        **kwargs
    ) -> Tuple[int, CacheLine]:
        """Find the way with minimum last_access timestamp."""
        best_idx = 0
        min_access = float("inf")
        for idx, line in enumerate(cache_set.ways):
            if line.last_access < min_access:
                min_access = line.last_access
                best_idx = idx
        return best_idx, cache_set.ways[best_idx]
