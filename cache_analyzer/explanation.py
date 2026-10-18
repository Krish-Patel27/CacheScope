"""
explanation.py — Automated architectural explanation engine for CacheScope.

Explains WHY cache performance changed between a baseline configuration and
an alternative experiment. Connects concrete metrics (hit rate, 3C misses, AMAT)
to computer-architecture principles (capacity, conflict, associativity, spatial locality).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from cache_analyzer.cache import CacheConfig
from cache_analyzer.metrics import CacheMetrics


@dataclass
class Explanation:
    """Structured architectural explanation of differences between two configurations."""

    title: str
    parameter_deltas: Dict[str, Any]
    metric_deltas: Dict[str, Any]
    primary_reason: str
    detailed_narrative: str
    evidence_points: List[str]

    def summary(self) -> str:
        """Formatted human-readable explanation."""
        points = "\n".join(f"  * {p}" for p in self.evidence_points)
        return (
            f"=== CacheScope Architectural Explanation ===\n"
            f"[{self.title}]\n"
            f"Primary Cause : {self.primary_reason}\n\n"
            f"Analysis Narrative:\n{self.detailed_narrative}\n\n"
            f"Supporting Evidence:\n{points}\n"
            f"============================================="
        )


class ExplanationEngine:
    """Analyzes pairs of simulation results and synthesizes pedagogical explanations."""

    def explain(
        self,
        base_config: CacheConfig,
        base_metrics: CacheMetrics,
        alt_config: CacheConfig,
        alt_metrics: CacheMetrics,
    ) -> Explanation:
        """Generate a complete architectural explanation comparing alt to base."""
        param_deltas: Dict[str, Any] = {}
        if alt_config.cache_size != base_config.cache_size:
            param_deltas["cache_size"] = (base_config.cache_size, alt_config.cache_size)
        if alt_config.block_size != base_config.block_size:
            param_deltas["block_size"] = (base_config.block_size, alt_config.block_size)
        if alt_config.associativity != base_config.associativity:
            param_deltas["associativity"] = (base_config.associativity, alt_config.associativity)
        if alt_config.replacement_policy != base_config.replacement_policy:
            param_deltas["replacement_policy"] = (base_config.replacement_policy, alt_config.replacement_policy)

        # Metric deltas
        hit_rate_diff = alt_metrics.hit_rate - base_metrics.hit_rate
        amat_diff = alt_metrics.amat - base_metrics.amat
        conflict_diff = alt_metrics.conflict_misses - base_metrics.conflict_misses
        capacity_diff = alt_metrics.capacity_misses - base_metrics.capacity_misses
        eviction_diff = alt_metrics.evictions - base_metrics.evictions

        metric_deltas = {
            "hit_rate_diff": round(hit_rate_diff, 2),
            "amat_diff": round(amat_diff, 3),
            "conflict_diff": conflict_diff,
            "capacity_diff": capacity_diff,
            "eviction_diff": eviction_diff,
        }

        # Build evidence points
        evidence: List[str] = []
        if hit_rate_diff > 0:
            evidence.append(f"Hit rate improved by +{hit_rate_diff:.2f}% (from {base_metrics.hit_rate:.2f}% to {alt_metrics.hit_rate:.2f}%).")
        elif hit_rate_diff < 0:
            evidence.append(f"Hit rate degraded by {hit_rate_diff:.2f}% (from {base_metrics.hit_rate:.2f}% to {alt_metrics.hit_rate:.2f}%).")
        else:
            evidence.append(f"Hit rate was unchanged at {base_metrics.hit_rate:.2f}%.")

        if amat_diff < 0:
            evidence.append(f"Average Memory Access Time (AMAT) improved by {abs(amat_diff):.3f} cycles (from {base_metrics.amat:.3f} to {alt_metrics.amat:.3f}).")
        elif amat_diff > 0:
            evidence.append(f"AMAT worsened by +{amat_diff:.3f} cycles (from {base_metrics.amat:.3f} to {alt_metrics.amat:.3f}).")

        if conflict_diff != 0:
            evidence.append(f"Conflict misses changed by {conflict_diff:+d} (from {base_metrics.conflict_misses} to {alt_metrics.conflict_misses}).")
        if capacity_diff != 0:
            evidence.append(f"Capacity misses changed by {capacity_diff:+d} (from {base_metrics.capacity_misses} to {alt_metrics.capacity_misses}).")
        if eviction_diff != 0:
            evidence.append(f"Total evictions changed by {eviction_diff:+d} (from {base_metrics.evictions} to {alt_metrics.evictions}).")

        # Synthesize architectural narrative
        title, primary_reason, narrative = self._synthesize_narrative(
            base_config, base_metrics, alt_config, alt_metrics, param_deltas, metric_deltas
        )

        return Explanation(
            title=title,
            parameter_deltas=param_deltas,
            metric_deltas=metric_deltas,
            primary_reason=primary_reason,
            detailed_narrative=narrative,
            evidence_points=evidence,
        )

    def _synthesize_narrative(
        self,
        base_cfg: CacheConfig,
        base_met: CacheMetrics,
        alt_cfg: CacheConfig,
        alt_met: CacheMetrics,
        param_deltas: Dict[str, Any],
        metric_deltas: Dict[str, Any],
    ) -> Tuple[str, str, str]:
        """Produce the specific architectural explanation text based on changed parameters."""
        hr_diff = metric_deltas["hit_rate_diff"]

        # Case 1: Pure Associativity Change
        if "associativity" in param_deltas and len(param_deltas) == 1:
            old_assoc, new_assoc = param_deltas["associativity"]
            if new_assoc > old_assoc:
                title = f"Associativity Expansion ({old_assoc}-Way -> {new_assoc}-Way)"
                primary = "Conflict miss reduction via increased set-associative ways"
                narrative = (
                    f"Cache size ({base_cfg.cache_size}B) and block size ({base_cfg.block_size}B) remained identical. "
                    f"Associativity increased from {old_assoc}-way to {new_assoc}-way. "
                    f"This allows up to {new_assoc} distinct memory blocks that hash to the same set index to coexist "
                    f"simultaneously without immediately evicting each other. "
                    f"As a result, conflict misses changed by {metric_deltas['conflict_diff']:+d}. "
                    f"The observed hit rate shift of {hr_diff:+.2f}% directly reflects reduced set contention."
                )
            else:
                title = f"Associativity Reduction ({old_assoc}-Way -> {new_assoc}-Way)"
                primary = "Increased set contention and conflict misses"
                narrative = (
                    f"Associativity decreased from {old_assoc}-way to {new_assoc}-way with cache size fixed. "
                    f"With fewer candidate ways per set, competing memory blocks sharing a set index forced "
                    f"more frequent line evictions, raising conflict misses by {metric_deltas['conflict_diff']:+d}."
                )
            return title, primary, narrative

        # Case 2: Pure Cache Size Change
        if "cache_size" in param_deltas and len(param_deltas) == 1:
            old_sz, new_sz = param_deltas["cache_size"]
            if new_sz > old_sz:
                title = f"Capacity Increase ({old_sz//1024}KB -> {new_sz//1024}KB)"
                primary = "Working set accommodation and capacity miss reduction"
                narrative = (
                    f"Cache capacity expanded from {old_sz} bytes to {new_sz} bytes while preserving block size "
                    f"and associativity. The larger cache accommodates a greater fraction of the program's working set, "
                    f"driving capacity misses down by {abs(metric_deltas['capacity_diff'])}. "
                    f"Total cache lines increased from {base_cfg.num_lines} to {alt_cfg.num_lines}, reducing the need "
                    f"to repeatedly evict previously loaded data."
                )
            else:
                title = f"Capacity Reduction ({old_sz//1024}KB -> {new_sz//1024}KB)"
                primary = "Working set eviction under reduced capacity"
                narrative = (
                    f"Cache capacity decreased from {old_sz} bytes to {new_sz} bytes. The working set no longer "
                    f"fits comfortably in cache, inducing additional capacity misses ({metric_deltas['capacity_diff']:+d})."
                )
            return title, primary, narrative

        # Case 3: Pure Block Size Change
        if "block_size" in param_deltas and len(param_deltas) == 1:
            old_bs, new_bs = param_deltas["block_size"]
            if new_bs > old_bs:
                title = f"Block Size Increase ({old_bs}B -> {new_bs}B)"
                primary = "Enhanced spatial locality vs total line count trade-off"
                narrative = (
                    f"Block size increased from {old_bs}B to {new_bs}B. Each cache line now fetches a larger contiguous "
                    f"slice of memory, exploiting spatial locality and turning neighboring memory accesses into instant hits. "
                    f"However, with total cache size fixed at {base_cfg.cache_size}B, the total number of lines dropped from "
                    f"{base_cfg.num_lines} to {alt_cfg.num_lines}. For workloads with high spatial locality this is a win, "
                    f"whereas for irregular or random workloads it can lead to higher cache pollution."
                )
            else:
                title = f"Block Size Decrease ({old_bs}B -> {new_bs}B)"
                primary = "Finer granularity lines with reduced spatial prefetch"
                narrative = (
                    f"Block size decreased from {old_bs}B to {new_bs}B, creating {alt_cfg.num_lines} smaller lines. "
                    f"While this reduces transfer waste for scattered accesses, it diminishes the automatic spatial "
                    f"prefetch benefit for contiguous sequential streams."
                )
            return title, primary, narrative

        # Case 4: Replacement Policy Change
        if "replacement_policy" in param_deltas and len(param_deltas) == 1:
            old_pol, new_pol = param_deltas["replacement_policy"]
            title = f"Replacement Policy Switch ({old_pol} -> {new_pol})"
            primary = f"Different eviction heuristic ({new_pol} instead of {old_pol})"
            narrative = (
                f"The physical cache geometry remained unchanged ({base_cfg.cache_size}B, {base_cfg.associativity}-way). "
                f"The difference in performance is entirely due to how victim lines are selected when sets become full. "
                f"{new_pol} prioritizes different access characteristics than {old_pol}, resulting in a hit rate "
                f"difference of {hr_diff:+.2f}%."
            )
            return title, primary, narrative

        # Case 5: Multi-parameter changes
        changed_keys = ", ".join(param_deltas.keys())
        title = f"Multi-Parameter Reconfiguration ({changed_keys})"
        primary = "Combined architectural impact of multiple parameters"
        narrative = (
            f"Multiple architectural parameters were modified concurrently: {changed_keys}. "
            f"Net hit rate shifted by {hr_diff:+.2f}% and AMAT moved by {metric_deltas['amat_diff']:+.3f} cycles. "
            f"Conflict misses shifted by {metric_deltas['conflict_diff']:+d} and capacity misses shifted by "
            f"{metric_deltas['capacity_diff']:+d}. Isolating individual parameters through single-variable "
            f"what-if runs is recommended to disentangle their independent effects."
        )
        return title, primary, narrative
