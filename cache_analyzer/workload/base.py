"""
base.py — Abstract base class for memory access workload generators.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class WorkloadGenerator(ABC):
    """Abstract interface for all memory access workload generators."""

    def __init__(self, name: str = "BaseWorkload", **kwargs):
        self.name: str = name
        self.params: Dict[str, Any] = kwargs

    @abstractmethod
    def generate(self) -> List[int]:
        """Generate and return a list of integer byte memory addresses."""
        pass

    def description(self) -> str:
        """User-friendly summary of the workload behavior and parameters."""
        return f"{self.name} with parameters: {self.params}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize workload configuration."""
        return {
            "name": self.name,
            "params": self.params,
            "description": self.description(),
        }
