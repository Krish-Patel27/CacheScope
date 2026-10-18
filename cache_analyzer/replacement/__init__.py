"""
replacement — Pluggable cache replacement policy framework.

Adding a new replacement policy is as simple as:
    from cache_analyzer.replacement import ReplacementPolicy, register_policy

    @register_policy("MY_POLICY")
    class MyCustomPolicy(ReplacementPolicy):
        def select_victim(self, cache_set, **kwargs):
            return 0, cache_set.ways[0]
"""

from typing import Callable, Dict, List, Type
from cache_analyzer.replacement.base import ReplacementPolicy
from cache_analyzer.replacement.lru import LRUPolicy
from cache_analyzer.replacement.fifo import FIFOPolicy
from cache_analyzer.replacement.lfu import LFUPolicy
from cache_analyzer.replacement.random_policy import RandomPolicy
from cache_analyzer.replacement.optimal import OptimalPolicy

POLICY_REGISTRY: Dict[str, Type[ReplacementPolicy]] = {}


def register_policy(name: str) -> Callable[[Type[ReplacementPolicy]], Type[ReplacementPolicy]]:
    """Decorator to register a custom replacement policy in the global registry."""
    def decorator(cls: Type[ReplacementPolicy]) -> Type[ReplacementPolicy]:
        key = name.strip().upper()
        POLICY_REGISTRY[key] = cls
        return cls
    return decorator


# Register built-in policies
register_policy("LRU")(LRUPolicy)
register_policy("FIFO")(FIFOPolicy)
register_policy("LFU")(LFUPolicy)
register_policy("RANDOM")(RandomPolicy)
register_policy("OPTIMAL")(OptimalPolicy)


def get_policy(name: str, **kwargs) -> ReplacementPolicy:
    """Instantiate a replacement policy by name (case-insensitive)."""
    key = name.strip().upper()
    if key not in POLICY_REGISTRY:
        raise ValueError(
            f"Unknown replacement policy '{name}'. "
            f"Available policies: {list(POLICY_REGISTRY.keys())}"
        )
    return POLICY_REGISTRY[key](**kwargs)


def available_policies() -> List[str]:
    """Return sorted list of all registered replacement policy names."""
    return sorted(POLICY_REGISTRY.keys())
