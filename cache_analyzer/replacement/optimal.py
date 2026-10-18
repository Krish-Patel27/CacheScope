"""
optimal.py — Bélády's Optimal (MIN) cache replacement policy.

Used as a theoretical upper bound (offline benchmark).
Evicts the block whose next access in the trace is farthest in the future.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from collections import deque
from cache_analyzer.replacement.base import ReplacementPolicy

if TYPE_CHECKING:
    from cache_analyzer.cache import CacheLine, CacheSet


class OptimalPolicy(ReplacementPolicy):
    """Bélády's Optimal (MIN) offline replacement policy.
    
    Requires knowledge of the upcoming memory trace. The simulator
    pre-indexes the next access position for each block or updates future access queues.
    """

    def __init__(self, **kwargs):
        super().__init__(name="OPTIMAL", **kwargs)
        # block_number -> deque of upcoming access step indices
        self.future_map: Dict[int, deque[int]] = {}

    def prepare_trace(self, block_sequence: List[int]):
        """Pre-index access steps for all blocks in the trace."""
        self.future_map.clear()
        for step, blk in enumerate(block_sequence):
            if blk not in self.future_map:
                self.future_map[blk] = deque()
            self.future_map[blk].append(step)

    def on_step_consumed(self, block_number: int, current_step: int):
        """Pop the current step occurrence for this block."""
        if block_number in self.future_map and self.future_map[block_number]:
            # Pop if the front is at or before current_step
            while self.future_map[block_number] and self.future_map[block_number][0] <= current_step:
                self.future_map[block_number].popleft()

    def select_victim(
        self,
        cache_set: CacheSet,
        **kwargs
    ) -> Tuple[int, CacheLine]:
        """Find the resident block whose next access is farthest in the future."""
        current_step = kwargs.get("current_step", 0)
        best_idx = 0
        furthest_distance = -1

        for idx, line in enumerate(cache_set.ways):
            blk = line.block_number
            if blk not in self.future_map or not self.future_map[blk]:
                # This block is NEVER accessed again in the entire remaining trace!
                # It is the best possible candidate for eviction.
                return idx, line

            next_step = self.future_map[blk][0]
            dist = next_step - current_step
            if dist > furthest_distance:
                furthest_distance = dist
                best_idx = idx

        return best_idx, cache_set.ways[best_idx]

    def reset(self):
        """Reset internal future map."""
        self.future_map.clear()
