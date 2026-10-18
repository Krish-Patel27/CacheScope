"""
cache.py — Core cache data structures and address decomposition geometry.

Supports:
- Direct-mapped caches (associativity = 1)
- Set-associative caches (1 < associativity < total_lines)
- Fully-associative caches (associativity = total_lines, 1 set)

Designed for maximum extensibility:
- CacheLine includes extensible metadata dictionary
- CacheSet tracks individual set-level access metrics
- CacheConfig validates geometry and calculates all bit offsets and tag splits
- Cache provides snapshot and hook capabilities for external monitors
"""

from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional, Tuple


class CacheLine:
    """Represents a single cache line (way) in a cache set.
    
    Attributes:
        valid: Whether this line currently holds valid data.
        tag: Memory tag stored in this line.
        block_number: Memory block index stored in this line.
        inserted_at: Timestamp (access count) when line was populated.
        last_access: Timestamp (access count) of most recent access.
        access_count: Total accesses to this line while continuously resident.
        dirty: Dirty flag for write-back policy extensions.
        metadata: Arbitrary dictionary for custom replacement policies.
    """
    __slots__ = (
        "valid", "tag", "block_number", "inserted_at",
        "last_access", "access_count", "dirty", "metadata"
    )

    def __init__(self):
        self.valid: bool = False
        self.tag: int = -1
        self.block_number: int = -1
        self.inserted_at: int = 0
        self.last_access: int = 0
        self.access_count: int = 0
        self.dirty: bool = False
        self.metadata: Dict[str, Any] = {}

    def clear(self):
        """Reset the line to invalid state."""
        self.valid = False
        self.tag = -1
        self.block_number = -1
        self.inserted_at = 0
        self.last_access = 0
        self.access_count = 0
        self.dirty = False
        self.metadata.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serializable representation of the line."""
        return {
            "valid": self.valid,
            "tag": self.tag,
            "block_number": self.block_number,
            "inserted_at": self.inserted_at,
            "last_access": self.last_access,
            "access_count": self.access_count,
            "dirty": self.dirty,
            "metadata": dict(self.metadata),
        }


class CacheSet:
    """Represents one cache set containing N ways (CacheLines)."""

    def __init__(self, set_index: int, associativity: int):
        self.set_index: int = set_index
        self.associativity: int = associativity
        self.ways: List[CacheLine] = [CacheLine() for _ in range(associativity)]
        
        # Set-specific statistics
        self.access_count: int = 0
        self.hit_count: int = 0
        self.miss_count: int = 0
        self.eviction_count: int = 0
        self.access_history: List[int] = []  # recent block numbers accessed

    def find_line(self, tag: int) -> Optional[Tuple[int, CacheLine]]:
        """Search set for a matching valid tag.
        
        Returns:
            Tuple of (way_index, line) if found, else None.
        """
        for way_idx, line in enumerate(self.ways):
            if line.valid and line.tag == tag:
                return way_idx, line
        return None

    def find_empty_way(self) -> Optional[Tuple[int, CacheLine]]:
        """Find the first available invalid (empty) way.
        
        Returns:
            Tuple of (way_index, line) if an empty way exists, else None.
        """
        for way_idx, line in enumerate(self.ways):
            if not line.valid:
                return way_idx, line
        return None

    @property
    def is_full(self) -> bool:
        """Check if all ways in this set are valid."""
        return all(line.valid for line in self.ways)

    @property
    def valid_count(self) -> int:
        """Count how many lines currently store valid data."""
        return sum(1 for line in self.ways if line.valid)

    def reset(self):
        """Reset set state and all ways."""
        self.access_count = 0
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        self.access_history.clear()
        for line in self.ways:
            line.clear()


class CacheConfig:
    """Immutable cache architecture geometry and timing configuration.
    
    Calculates derived geometry:
    - Number of cache lines = cache_size / block_size
    - Number of sets = number_of_cache_lines / associativity
    - Offset bits = log2(block_size)
    - Set-index bits = log2(number_of_sets)
    - Tag bits = address_bits - offset_bits - set_index_bits
    """

    def __init__(
        self,
        cache_size: int = 4096,
        block_size: int = 64,
        associativity: int = 1,
        address_bits: int = 32,
        replacement_policy: str = "LRU",
        hit_time: float = 1.0,
        miss_penalty: float = 100.0,
        name: str = "CacheConfig",
        extra_params: Optional[Dict[str, Any]] = None,
    ):
        if cache_size <= 0:
            raise ValueError(f"Cache size must be positive, got {cache_size}")
        if block_size <= 0:
            raise ValueError(f"Block size must be positive, got {block_size}")
        if cache_size < block_size:
            raise ValueError(
                f"Cache size ({cache_size}B) cannot be smaller than block size ({block_size}B)"
            )

        self.cache_size = cache_size
        self.block_size = block_size
        self.address_bits = address_bits
        self.replacement_policy = replacement_policy.upper()
        self.hit_time = hit_time
        self.miss_penalty = miss_penalty
        self.name = name
        self.extra_params = extra_params or {}

        # Determine lines
        self.num_lines = cache_size // block_size

        # Handle fully-associative shorthand: associativity <= 0 or None -> num_lines
        if associativity is None or associativity <= 0 or associativity >= self.num_lines:
            self.associativity = self.num_lines
            self.num_sets = 1
            self.is_fully_associative = True
            self.is_direct_mapped = (self.num_lines == 1)
        else:
            self.associativity = associativity
            self.num_sets = self.num_lines // self.associativity
            self.is_fully_associative = False
            self.is_direct_mapped = (self.associativity == 1)

        if self.num_lines % self.associativity != 0:
            raise ValueError(
                f"Total lines ({self.num_lines}) must be divisible by associativity ({self.associativity})"
            )

        # Bit breakdowns (assuming power of two geometry, with fallbacks)
        self.offset_bits = int(round(math.log2(self.block_size))) if self.block_size > 0 else 0
        self.index_bits = int(round(math.log2(self.num_sets))) if self.num_sets > 0 else 0
        self.tag_bits = max(0, self.address_bits - self.offset_bits - self.index_bits)

    # ---------------- Address Parsing ---------------- #

    def block_number(self, address: int) -> int:
        """Calculate memory block number from byte address: address // block_size."""
        return address // self.block_size

    def offset(self, address: int) -> int:
        """Calculate byte offset within block: address % block_size."""
        return address % self.block_size

    def set_index(self, block_num: int) -> int:
        """Calculate mapped cache set index: block_number % number_of_sets."""
        if self.num_sets <= 1:
            return 0
        return block_num % self.num_sets

    def tag(self, block_num: int) -> int:
        """Calculate tag identifier: block_number // number_of_sets."""
        if self.num_sets <= 1:
            return block_num
        return block_num // self.num_sets

    def decompose(self, address: int) -> Dict[str, Any]:
        """Decompose address into complete architectural breakdown."""
        blk = self.block_number(address)
        off = self.offset(address)
        idx = self.set_index(blk)
        t = self.tag(blk)
        return {
            "address": address,
            "address_hex": hex(address),
            "block_number": blk,
            "set_index": idx,
            "tag": t,
            "offset": off,
            "tag_hex": hex(t),
            "tag_bits": self.tag_bits,
            "index_bits": self.index_bits,
            "offset_bits": self.offset_bits,
        }

    def organization_str(self) -> str:
        """Human-readable organization label."""
        if self.is_direct_mapped:
            return "Direct-Mapped (1-Way)"
        if self.is_fully_associative:
            return f"Fully Associative ({self.num_lines}-Way, 1 Set)"
        return f"{self.associativity}-Way Set-Associative ({self.num_sets} Sets)"

    def summary(self) -> str:
        """Detailed geometry summary string."""
        return (
            f"[{self.name}] Size: {self.cache_size}B ({self.cache_size // 1024}KB) | "
            f"Block: {self.block_size}B | "
            f"Org: {self.organization_str()} | "
            f"Lines: {self.num_lines} | Sets: {self.num_sets} | "
            f"Bits (Tag/Index/Offset): {self.tag_bits}/{self.index_bits}/{self.offset_bits} | "
            f"Policy: {self.replacement_policy}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Export config parameters to dictionary."""
        return {
            "name": self.name,
            "cache_size": self.cache_size,
            "block_size": self.block_size,
            "associativity": self.associativity,
            "num_lines": self.num_lines,
            "num_sets": self.num_sets,
            "offset_bits": self.offset_bits,
            "index_bits": self.index_bits,
            "tag_bits": self.tag_bits,
            "replacement_policy": self.replacement_policy,
            "hit_time": self.hit_time,
            "miss_penalty": self.miss_penalty,
            "organization": self.organization_str(),
        }

    def clone_with(self, **kwargs) -> CacheConfig:
        """Create a modified copy of this configuration (useful for what-if explorations)."""
        current = {
            "cache_size": self.cache_size,
            "block_size": self.block_size,
            "associativity": self.associativity,
            "address_bits": self.address_bits,
            "replacement_policy": self.replacement_policy,
            "hit_time": self.hit_time,
            "miss_penalty": self.miss_penalty,
            "name": self.name,
            "extra_params": dict(self.extra_params),
        }
        current.update(kwargs)
        return CacheConfig(**current)

    def __repr__(self) -> str:
        return (
            f"CacheConfig(size={self.cache_size}, block={self.block_size}, "
            f"assoc={self.associativity}, sets={self.num_sets}, policy='{self.replacement_policy}')"
        )


class Cache:
    """The hardware cache model containing sets, ways, and access clock."""

    def __init__(self, config: CacheConfig):
        self.config: CacheConfig = config
        self.sets: List[CacheSet] = [
            CacheSet(i, config.associativity) for i in range(config.num_sets)
        ]
        self._access_counter: int = 0
        
        # Extensible hooks for monitoring, debugging, or custom instrumentation
        self.pre_access_hooks: List[Callable[[int, int], None]] = []
        self.post_access_hooks: List[Callable[[int, bool, int, int], None]] = []

    @property
    def access_counter(self) -> int:
        """Global monotonic access timestamp counter."""
        return self._access_counter

    def tick(self) -> int:
        """Increment and return the simulation clock."""
        self._access_counter += 1
        return self._access_counter

    def get_set(self, set_index: int) -> CacheSet:
        """Retrieve a specific cache set by index."""
        return self.sets[set_index]

    def reset(self):
        """Reset all sets and internal state."""
        self._access_counter = 0
        for s in self.sets:
            s.reset()

    def get_snapshot(self) -> List[Dict[str, Any]]:
        """Return a structured snapshot of all sets and ways."""
        snapshot = []
        for s in self.sets:
            snapshot.append({
                "set_index": s.set_index,
                "access_count": s.access_count,
                "hit_count": s.hit_count,
                "miss_count": s.miss_count,
                "eviction_count": s.eviction_count,
                "ways": [w.to_dict() for w in s.ways],
            })
        return snapshot

    def get_occupancy_ratio(self) -> float:
        """Percentage of total lines currently holding valid data."""
        total_valid = sum(s.valid_count for s in self.sets)
        return (total_valid / self.config.num_lines) if self.config.num_lines > 0 else 0.0
