"""
loop.py — Looping memory access trace generator.

Simulates loops over arrays or buffers. Shows cache behavior when the loop size
is smaller than, equal to, or larger than the cache (demonstrating cache thrashing).
"""

from __future__ import annotations
from typing import List
from cache_analyzer.workload.base import WorkloadGenerator


class LoopWorkload(WorkloadGenerator):
    """Repeats a sequence of memory block addresses across multiple iterations.
    
    If loop working set fits in cache: hits on all iterations after first.
    If loop working set exceeds cache lines by even 1 block with LRU/FIFO: thrashing occurs!
    """

    def __init__(
        self,
        base_address: int = 0x1000,
        num_elements: int = 80,
        element_size: int = 64,
        iterations: int = 6,
        **kwargs
    ):
        super().__init__(
            name="LOOP",
            base_address=base_address,
            num_elements=num_elements,
            element_size=element_size,
            iterations=iterations,
            **kwargs
        )
        self.base_address = base_address
        self.num_elements = num_elements
        self.element_size = element_size
        self.iterations = iterations

    def generate(self) -> List[int]:
        loop_pattern = [
            self.base_address + i * self.element_size
            for i in range(self.num_elements)
        ]
        trace: List[int] = []
        for _ in range(self.iterations):
            trace.extend(loop_pattern)
        return trace

    def description(self) -> str:
        working_set_bytes = self.num_elements * self.element_size
        return (
            f"Loop trace: {self.num_elements} elements of {self.element_size}B "
            f"(working set={working_set_bytes}B), repeated for {self.iterations} iterations "
            f"(total={self.num_elements * self.iterations} accesses)"
        )
