"""
metrics.py — Cache performance metrics calculation and 3C miss classification.

Calculates:
- Hits, Misses, Hit Rate (%), Miss Rate (%)
- Evictions Count
- Compulsory (Cold), Capacity, and Conflict Miss classification
- Average Memory Access Time (AMAT) for single-level and two-level caches
- Set utilization and access skew metrics
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from cache_analyzer.cache import Cache, CacheConfig


@dataclass
class CacheMetrics:
    """Consolidated performance metrics for a simulation run."""

    total_accesses: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0          # percentage (0.0 to 100.0)
    miss_rate: float = 0.0         # percentage (0.0 to 100.0)
    evictions: int = 0

    # 3C Miss Classification
    compulsory_misses: int = 0
    capacity_misses: int = 0
    conflict_misses: int = 0
    compulsory_rate: float = 0.0   # % of total misses
    capacity_rate: float = 0.0     # % of total misses
    conflict_rate: float = 0.0     # % of total misses

    # Timing / AMAT
    hit_time: float = 1.0
    miss_penalty: float = 100.0
    amat: float = 0.0

    # Set utilization distribution
    set_access_counts: List[int] = field(default_factory=list)
    active_sets: int = 0
    empty_sets: int = 0
    max_set_accesses: int = 0
    min_set_accesses: int = 0
    utilization_variance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a flat dictionary for reporting, exports, and databases."""
        return {
            "total_accesses": self.total_accesses,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hit_rate, 2),
            "miss_rate": round(self.miss_rate, 2),
            "evictions": self.evictions,
            "compulsory_misses": self.compulsory_misses,
            "capacity_misses": self.capacity_misses,
            "conflict_misses": self.conflict_misses,
            "compulsory_pct_of_misses": round(self.compulsory_rate, 2),
            "capacity_pct_of_misses": round(self.capacity_rate, 2),
            "conflict_pct_of_misses": round(self.conflict_rate, 2),
            "hit_time": self.hit_time,
            "miss_penalty": self.miss_penalty,
            "amat": round(self.amat, 3),
            "active_sets": self.active_sets,
            "empty_sets": self.empty_sets,
            "max_set_accesses": self.max_set_accesses,
            "min_set_accesses": self.min_set_accesses,
            "utilization_variance": round(self.utilization_variance, 2),
        }

    def summary(self) -> str:
        """Formatted human-readable summary card."""
        return (
            f"=== Cache Performance Summary ===\n"
            f"Total Accesses : {self.total_accesses:,}\n"
            f"Hits           : {self.hits:,} ({self.hit_rate:.2f}%)\n"
            f"Misses         : {self.misses:,} ({self.miss_rate:.2f}%)\n"
            f"Evictions      : {self.evictions:,}\n"
            f"AMAT           : {self.amat:.3f} cycles (Hit: {self.hit_time}, Penalty: {self.miss_penalty})\n"
            f"--- 3C Miss Breakdown ---\n"
            f"Compulsory (Cold) : {self.compulsory_misses:,} ({self.compulsory_rate:.1f}% of misses)\n"
            f"Capacity          : {self.capacity_misses:,} ({self.capacity_rate:.1f}% of misses)\n"
            f"Conflict          : {self.conflict_misses:,} ({self.conflict_rate:.1f}% of misses)\n"
            f"--- Set Utilization ---\n"
            f"Active Sets    : {self.active_sets} / {len(self.set_access_counts)}\n"
            f"Max Set Hits   : {self.max_set_accesses:,} | Min: {self.min_set_accesses:,}"
        )


def calculate_amat(
    hit_rate: float,
    hit_time: float,
    miss_penalty: float,
    l2_metrics: Optional[Dict[str, float]] = None,
) -> float:
    """Calculate Average Memory Access Time (AMAT).
    
    Formula: AMAT = Hit_Time + Miss_Rate * Miss_Penalty
    
    If l2_metrics provided:
    L1 AMAT = L1_Hit_Time + L1_Miss_Rate * (L2_Hit_Time + L2_Miss_Rate * L2_Penalty)
    """
    miss_rate_frac = (100.0 - hit_rate) / 100.0
    if l2_metrics:
        l2_hit_time = l2_metrics.get("hit_time", 10.0)
        l2_miss_rate = l2_metrics.get("miss_rate", 0.1)
        l2_penalty = l2_metrics.get("miss_penalty", 100.0)
        effective_miss_penalty = l2_hit_time + (l2_miss_rate * l2_penalty)
        return hit_time + (miss_rate_frac * effective_miss_penalty)

    return hit_time + (miss_rate_frac * miss_penalty)


def classify_misses(
    events: List[Any],
    total_blocks_in_cache: int,
    policy_name: str = "LRU",
) -> Dict[str, int]:
    """Accurately classify all misses in a simulation run using the standard 3C model.
    
    Academic 3C Model (Hennessy & Patterson):
    1. Compulsory (Cold): First time this memory block is EVER referenced in the trace.
    2. Capacity: Miss is NOT compulsory, AND it would also miss in a Fully Associative cache
       of the SAME capacity (same number of total cache lines).
    3. Conflict: Miss is NOT compulsory, BUT it WOULD HIT in a Fully Associative cache
       of the same capacity. (Caused purely by mapping restrictions of set associativity).
    """
    seen_blocks: Set[int] = set()
    compulsory_count = 0
    capacity_count = 0
    conflict_count = 0

    # Simulate an equivalent Fully-Associative cache of the same capacity
    fa_cache: List[int] = []  # list of resident block numbers, ordered by recency for LRU

    for ev in events:
        blk = ev.block_number
        is_hit = ev.is_hit

        # Check Fully-Associative status
        fa_hit = blk in fa_cache
        if fa_hit:
            if policy_name == "LRU":
                fa_cache.remove(blk)
                fa_cache.append(blk)
        else:
            if len(fa_cache) < total_blocks_in_cache:
                fa_cache.append(blk)
            else:
                fa_cache.pop(0)  # evict oldest
                fa_cache.append(blk)

        if not is_hit:
            if blk not in seen_blocks:
                compulsory_count += 1
                ev.miss_type = "COMPULSORY"
            elif not fa_hit:
                capacity_count += 1
                ev.miss_type = "CAPACITY"
            else:
                conflict_count += 1
                ev.miss_type = "CONFLICT"
        else:
            ev.miss_type = None

        seen_blocks.add(blk)

    return {
        "compulsory": compulsory_count,
        "capacity": capacity_count,
        "conflict": conflict_count,
    }


def calculate_metrics(
    cache: Cache,
    events: List[Any],
    hit_time: float,
    miss_penalty: float,
) -> CacheMetrics:
    """Compute complete metrics from cache state and recorded access events."""
    total_accesses = len(events)
    if total_accesses == 0:
        return CacheMetrics(hit_time=hit_time, miss_penalty=miss_penalty)

    hits = sum(1 for e in events if e.is_hit)
    misses = total_accesses - hits
    evictions = sum(1 for e in events if e.evicted_block is not None)

    hit_rate = (hits / total_accesses) * 100.0
    miss_rate = (misses / total_accesses) * 100.0

    # 3C Classification
    classification = classify_misses(
        events,
        total_blocks_in_cache=cache.config.num_lines,
        policy_name=cache.config.replacement_policy,
    )
    compulsory = classification["compulsory"]
    capacity = classification["capacity"]
    conflict = classification["conflict"]

    compulsory_rate = (compulsory / misses * 100.0) if misses > 0 else 0.0
    capacity_rate = (capacity / misses * 100.0) if misses > 0 else 0.0
    conflict_rate = (conflict / misses * 100.0) if misses > 0 else 0.0

    amat = calculate_amat(hit_rate, hit_time, miss_penalty)

    # Set access distribution
    set_counts = [s.access_count for s in cache.sets]
    active_sets = sum(1 for c in set_counts if c > 0)
    empty_sets = len(set_counts) - active_sets
    max_set = max(set_counts) if set_counts else 0
    min_set = min(set_counts) if set_counts else 0

    mean_acc = (sum(set_counts) / len(set_counts)) if set_counts else 0.0
    variance = (
        sum((x - mean_acc) ** 2 for x in set_counts) / len(set_counts)
    ) if set_counts else 0.0

    return CacheMetrics(
        total_accesses=total_accesses,
        hits=hits,
        misses=misses,
        hit_rate=hit_rate,
        miss_rate=miss_rate,
        evictions=evictions,
        compulsory_misses=compulsory,
        capacity_misses=capacity,
        conflict_misses=conflict,
        compulsory_rate=compulsory_rate,
        capacity_rate=capacity_rate,
        conflict_rate=conflict_rate,
        hit_time=hit_time,
        miss_penalty=miss_penalty,
        amat=amat,
        set_access_counts=set_counts,
        active_sets=active_sets,
        empty_sets=empty_sets,
        max_set_accesses=max_set,
        min_set_accesses=min_set,
        utilization_variance=variance,
    )
