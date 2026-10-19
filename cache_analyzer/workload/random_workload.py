"""
random_workload.py — Random memory access trace generator.
"""

from __future__ import annotations
import random
from typing import List, Optional
from cache_analyzer.workload.base import WorkloadGenerator


class RandomWorkload(WorkloadGenerator):
    """Generates pseudorandom memory addresses across a specified address range.
    
    Exhibits very low temporal and spatial locality, stressing cache capacity
    and replacement algorithms under pathological conditions.
    """

    def __init__(
        self,
        min_address: int = 0,
        max_address: int = 65536,
        alignment: int = 4,
        count: int = 1000,
        seed: Optional[int] = 42,
        **kwargs
    ):
        super().__init__(
            name="RANDOM",
            min_address=min_address,
            max_address=max_address,
            alignment=alignment,
            count=count,
            seed=seed,
            **kwargs
        )
        self.min_address = min_address
        self.max_address = max_address
        self.alignment = alignment
        self.count = count
        self.seed = seed

    def generate(self) -> List[int]:
        rng = random.Random(self.seed)
        step = max(1, self.alignment)
        addresses = []
        for _ in range(self.count):
            addr = rng.randrange(self.min_address, self.max_address, step)
            addresses.append(addr)
        return addresses

    def description(self) -> str:
        return (
            f"Random trace between 0x{self.min_address:X} and 0x{self.max_address:X}, "
            f"alignment={self.alignment}B, count={self.count}, seed={self.seed}"
        )
