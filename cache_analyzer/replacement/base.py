"""
base.py — Abstract base class for pluggable cache replacement policies.

Any replacement strategy can be implemented by subclassing ReplacementPolicy
and registering it using @register_policy.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from cache_analyzer.cache import CacheLine, CacheSet


class ReplacementPolicy(ABC):
    """Abstract interface for cache block replacement policies."""

    def __init__(self, name: str = "BasePolicy", **kwargs):
        self.name: str = name
        self.params: Dict[str, Any] = kwargs

    @abstractmethod
    def select_victim(
        self,
        cache_set: CacheSet,
        **kwargs
    ) -> Tuple[int, CacheLine]:
        """Select a victim way to be evicted from a full cache set.
        
        Parameters:
            cache_set: The full CacheSet from which to evict a line.
            **kwargs: Extra runtime context (e.g. future_accesses, current_step).
            
        Returns:
            Tuple of (victim_way_index, victim_CacheLine).
        """
        pass

    def on_hit(
        self,
        line: CacheLine,
        way_idx: int,
        cache_set: CacheSet,
        access_counter: int,
        **kwargs
    ):
        """Hook triggered whenever an access hits in the cache."""
        line.last_access = access_counter
        line.access_count += 1

    def on_insert(
        self,
        line: CacheLine,
        way_idx: int,
        cache_set: CacheSet,
        tag: int,
        block_number: int,
        access_counter: int,
        **kwargs
    ):
        """Hook triggered when a new block is placed into a way (empty or after eviction)."""
        line.valid = True
        line.tag = tag
        line.block_number = block_number
        line.inserted_at = access_counter
        line.last_access = access_counter
        line.access_count = 1
        line.dirty = False

    def on_evict(
        self,
        line: CacheLine,
        way_idx: int,
        cache_set: CacheSet,
        access_counter: int,
        **kwargs
    ):
        """Hook triggered just before a line is evicted."""
        pass

    def reset(self):
        """Reset policy-specific state across simulation runs."""
        pass

    def description(self) -> str:
        """User-friendly summary of policy behavior."""
        return self.__doc__ or self.__class__.__name__
