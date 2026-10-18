"""
sequential.py — Sequential memory access workload generator.
"""

from __future__ import annotations
from typing import List
from cache_analyzer.workload.base import WorkloadGenerator


class SequentialWorkload(WorkloadGenerator):
    """Generates a linear sequence of memory addresses with a fixed stride.
    
    Excellent for testing spatial locality and cache block prefetching behavior.
    """

    def __init__(
        self,
        start_address: int = 0,
        stride: int = 4,
        count: int = 1024,
        **kwargs
    ):
        super().__init__(
            name="SEQUENTIAL",
            start_address=start_address,
            stride=stride,
            count=count,
            **kwargs
        )
        self.start_address = start_address
        self.stride = stride
        self.count = count

    def generate(self) -> List[int]:
        """Produce consecutive addresses advancing by stride across repeated passes."""
        addresses: List[int] = []
        # Access a working set vector across repeated passes so temporal reuse exercises cache capacity
        vector_len = max(32, self.count // 2)
        while len(addresses) < self.count:
            for i in range(vector_len):
                addresses.append(self.start_address + i * self.stride)
                if len(addresses) >= self.count:
                    break
        return addresses

    def description(self) -> str:
        return (
            f"Sequential trace starting at 0x{self.start_address:X}, "
            f"stride={self.stride} bytes, count={self.count} accesses"
        )
