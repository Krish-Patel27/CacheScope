"""
simulator.py — End-to-end Cache Simulation Engine.

Executes memory access traces against cache geometries and replacement policies.
Records every access event, tracks resident blocks, and computes metrics.
Supports both batch runs and step-by-step interactive inspection.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from cache_analyzer.cache import Cache, CacheConfig, CacheLine
from cache_analyzer.metrics import CacheMetrics, calculate_metrics
from cache_analyzer.replacement import get_policy, ReplacementPolicy
from cache_analyzer.replacement.optimal import OptimalPolicy


@dataclass
class AccessEvent:
    """Detailed record of a single memory access event."""

    step: int
    address: int
    address_hex: str
    block_number: int
    set_index: int
    tag: int
    offset: int
    is_hit: bool
    way_index: int
    evicted_block: Optional[int] = None
    victim_way: Optional[int] = None
    miss_type: Optional[str] = None  # COMPULSORY, CAPACITY, CONFLICT, or None
    resident_tags_in_set: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to flat dictionary."""
        return {
            "step": self.step,
            "address": self.address,
            "address_hex": self.address_hex,
            "block_number": self.block_number,
            "set_index": self.set_index,
            "tag": self.tag,
            "offset": self.offset,
            "is_hit": self.is_hit,
            "result": "HIT" if self.is_hit else "MISS",
            "way_index": self.way_index,
            "evicted_block": self.evicted_block,
            "victim_way": self.victim_way,
            "miss_type": self.miss_type or "",
            "resident_tags": list(self.resident_tags_in_set),
        }


@dataclass
class SimulationResult:
    """Consolidated outcome of a full simulation run."""

    config: CacheConfig
    workload_name: str
    events: List[AccessEvent]
    metrics: CacheMetrics
    execution_time_ms: float = 0.0
    final_cache_snapshot: List[Dict[str, Any]] = field(default_factory=list)

    def __getattr__(self, name: str) -> Any:
        if name == "final_cache_snapshot":
            return []
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "config": self.config.to_dict(),
            "workload_name": self.workload_name,
            "metrics": self.metrics.to_dict(),
            "total_events": len(self.events),
            "execution_time_ms": round(self.execution_time_ms, 2),
        }

    def summary(self) -> str:
        """Formatted textual report."""
        return (
            f"==========================================================\n"
            f"CacheScope Simulation Report: {self.workload_name}\n"
            f"Configuration: {self.config.summary()}\n"
            f"Execution Time: {self.execution_time_ms:.2f} ms\n"
            f"==========================================================\n"
            f"{self.metrics.summary()}\n"
            f"=========================================================="
        )


class CacheSimulator:
    """Core simulation engine executing address traces against a Cache."""

    def __init__(
        self,
        config: CacheConfig,
        policy: Optional[ReplacementPolicy] = None,
    ):
        self.config: CacheConfig = config
        self.cache: Cache = Cache(config)
        self.policy: ReplacementPolicy = policy or get_policy(config.replacement_policy)
        self.events: List[AccessEvent] = []
        self.step_listeners: List[Callable[[AccessEvent], None]] = []

    def reset(self):
        """Reset cache state, events, and replacement policy."""
        self.cache.reset()
        self.events.clear()
        self.policy.reset()

    def step(
        self,
        address: int,
        future_context: Optional[Dict[str, Any]] = None,
    ) -> AccessEvent:
        """Process a single memory address access through the cache.
        
        Follows the standard hardware cache lookup pipeline:
        1. Decompose address into block, offset, set_index, tag.
        2. Inspect mapped set.
        3. Hit: record hit, invoke policy.on_hit.
        4. Miss:
           a. If empty way exists: place new block, invoke policy.on_insert.
           b. If set is full: invoke policy.select_victim, evict victim, invoke policy.on_insert.
        5. Return AccessEvent.
        """
        clk = self.cache.tick()
        step_idx = len(self.events)

        blk = self.config.block_number(address)
        off = self.config.offset(address)
        set_idx = self.config.set_index(blk)
        tag = self.config.tag(blk)

        c_set = self.cache.get_set(set_idx)
        c_set.access_count += 1
        c_set.access_history.append(blk)

        # Notify Optimal policy if active
        if isinstance(self.policy, OptimalPolicy):
            self.policy.on_step_consumed(blk, step_idx)

        # Step 1: Check for Hit
        hit_result = c_set.find_line(tag)

        evicted_blk: Optional[int] = None
        victim_way_idx: Optional[int] = None

        if hit_result is not None:
            # --- HIT ---
            way_idx, line = hit_result
            c_set.hit_count += 1
            self.policy.on_hit(
                line=line,
                way_idx=way_idx,
                cache_set=c_set,
                access_counter=clk,
            )
            is_hit = True
        else:
            # --- MISS ---
            is_hit = False
            c_set.miss_count += 1

            # Check if there is an empty way in this set
            empty_result = c_set.find_empty_way()
            if empty_result is not None:
                # Insert without eviction
                way_idx, line = empty_result
                self.policy.on_insert(
                    line=line,
                    way_idx=way_idx,
                    cache_set=c_set,
                    tag=tag,
                    block_number=blk,
                    access_counter=clk,
                )
            else:
                # Set is FULL: Eviction required
                c_set.eviction_count += 1
                ctx = future_context or {}
                ctx["current_step"] = step_idx

                victim_idx, victim_line = self.policy.select_victim(
                    cache_set=c_set,
                    **ctx
                )
                evicted_blk = victim_line.block_number
                victim_way_idx = victim_idx

                # Trigger eviction hook
                self.policy.on_evict(
                    line=victim_line,
                    way_idx=victim_idx,
                    cache_set=c_set,
                    access_counter=clk,
                )

                # Overwrite victim line with new block
                way_idx = victim_idx
                line = victim_line
                self.policy.on_insert(
                    line=line,
                    way_idx=way_idx,
                    cache_set=c_set,
                    tag=tag,
                    block_number=blk,
                    access_counter=clk,
                )

        # Capture resident tags in set for visualization / auditing
        resident_tags = [w.tag for w in c_set.ways if w.valid]

        event = AccessEvent(
            step=step_idx,
            address=address,
            address_hex=hex(address),
            block_number=blk,
            set_index=set_idx,
            tag=tag,
            offset=off,
            is_hit=is_hit,
            way_index=way_idx,
            evicted_block=evicted_blk,
            victim_way=victim_way_idx,
            miss_type=None,
            resident_tags_in_set=resident_tags,
        )

        self.events.append(event)

        for listener in self.step_listeners:
            listener(event)

        return event

    def run(
        self,
        trace: List[int],
        workload_name: str = "CustomTrace",
    ) -> SimulationResult:
        """Run an entire memory access trace synchronously."""
        self.reset()
        start_time = time.perf_counter()

        # If using Optimal policy, prepare future block sequence for lookahead
        if isinstance(self.policy, OptimalPolicy):
            block_seq = [self.config.block_number(a) for a in trace]
            self.policy.prepare_trace(block_seq)

        for addr in trace:
            self.step(addr)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Calculate final metrics and 3C miss classification
        metrics = calculate_metrics(
            cache=self.cache,
            events=self.events,
            hit_time=self.config.hit_time,
            miss_penalty=self.config.miss_penalty,
        )

        return SimulationResult(
            config=self.config,
            workload_name=workload_name,
            events=self.events,
            metrics=metrics,
            execution_time_ms=elapsed_ms,
            final_cache_snapshot=self.cache.get_snapshot(),
        )
