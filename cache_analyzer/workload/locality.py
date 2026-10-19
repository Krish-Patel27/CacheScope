"""
locality.py — High-locality memory access trace generator.

Simulates realistic applications with 85/15 temporal and spatial locality.
Designed to exert realistic capacity and conflict pressure on cache architectures.
"""

from __future__ import annotations
import random
from typing import List, Optional
from cache_analyzer.workload.base import WorkloadGenerator


class LocalityWorkload(WorkloadGenerator):
    """Generates a trace with strong temporal and spatial locality.
    
    A hot working set receives the majority of accesses (temporal locality),
    and nearby addresses are frequently accessed in bursts (spatial locality).
    """

    def __init__(
        self,
        base_address: int = 0x2000,
        hot_set_size: int = 32,
        cold_set_size: int = 160,
        block_size: int = 64,
        hot_ratio: float = 0.80,
        burst_length: int = 4,
        count: int = 1000,
        seed: Optional[int] = 42,
        **kwargs
    ):
        super().__init__(
            name="LOCALITY",
            base_address=base_address,
            hot_set_size=hot_set_size,
            cold_set_size=cold_set_size,
            block_size=block_size,
            hot_ratio=hot_ratio,
            burst_length=burst_length,
            count=count,
            seed=seed,
            **kwargs
        )
        self.base_address = base_address
        self.hot_set_size = hot_set_size
        self.cold_set_size = cold_set_size
        self.block_size = block_size
        self.hot_ratio = hot_ratio
        self.burst_length = burst_length
        self.count = count
        self.seed = seed

    def generate(self) -> List[int]:
        rng = random.Random(self.seed)
        # Partition hot set into collaborating memory streams that map across the same cache sets
        # (models real multi-array / multi-variable set contention as in Section 3.2 of specification)
        half_hot = max(4, self.hot_set_size // 2)
        stream_a = [self.base_address + i * self.block_size for i in range(half_hot)]
        # Stream B offset by 4096 (power-of-2 alias) to compete for the same set indices
        stream_b = [self.base_address + 4096 + i * self.block_size for i in range(half_hot)]
        hot_blocks = stream_a + stream_b
        cold_blocks = [
            self.base_address + 16384 + i * self.block_size
            for i in range(self.cold_set_size)
        ]

        trace: List[int] = []
        while len(trace) < self.count:
            # Choose hot or cold block
            if rng.random() < self.hot_ratio:
                anchor = rng.choice(hot_blocks)
            else:
                anchor = rng.choice(cold_blocks)

            # Spatial burst: access consecutive bytes within or near this block
            burst = min(self.burst_length, self.count - len(trace))
            for b in range(burst):
                offset = (b * 8) % self.block_size
                trace.append(anchor + offset)

        return trace

    def description(self) -> str:
        total_blocks = self.hot_set_size + self.cold_set_size
        working_set_bytes = total_blocks * self.block_size
        return (
            f"Locality trace: {self.hot_set_size} hot blocks ({self.hot_ratio*100:.0f}% accesses), "
            f"{self.cold_set_size} cold blocks (working set={working_set_bytes}B), count={self.count} accesses"
        )
