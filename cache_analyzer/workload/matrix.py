"""
matrix.py — 2D Matrix traversal workload generator.

Simulates matrix operations (Row-Major vs Column-Major traversals).
Demonstrates the classic performance pitfall of column-major access in C/C++/Python
where stride equals row_width * element_size, causing high cache miss rates.
"""

from __future__ import annotations
from typing import List
from cache_analyzer.workload.base import WorkloadGenerator


class MatrixWorkload(WorkloadGenerator):
    """Generates 2D matrix element access traces in row-major or column-major order."""

    def __init__(
        self,
        rows: int = 32,
        cols: int = 32,
        element_size: int = 8,
        order: str = "row-major",
        base_address: int = 0x4000,
        **kwargs
    ):
        super().__init__(
            name="MATRIX",
            rows=rows,
            cols=cols,
            element_size=element_size,
            order=order.lower(),
            base_address=base_address,
            **kwargs
        )
        self.rows = rows
        self.cols = cols
        self.element_size = element_size
        self.order = order.lower()
        self.base_address = base_address

    def generate(self) -> List[int]:
        addresses: List[int] = []
        # Simulate 2-pass matrix operation (e.g. read/transform pass + reduction/verify pass)
        for _ in range(2):
            if self.order == "row-major":
                # Outer loop over rows, inner loop over columns (cache friendly)
                for r in range(self.rows):
                    for c in range(self.cols):
                        addr = self.base_address + (r * self.cols + c) * self.element_size
                        addresses.append(addr)
            else:
                # Outer loop over columns, inner loop over rows (strided / cache unfriendly)
                for c in range(self.cols):
                    for r in range(self.rows):
                        addr = self.base_address + (r * self.cols + c) * self.element_size
                        addresses.append(addr)
        return addresses

    def description(self) -> str:
        matrix_bytes = self.rows * self.cols * self.element_size
        return (
            f"Matrix trace: {self.rows}x{self.cols} ({self.element_size}B elements, total={matrix_bytes}B), "
            f"order={self.order.upper()} (total={self.rows * self.cols} accesses)"
        )
