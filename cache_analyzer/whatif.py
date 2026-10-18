"""
whatif.py — What-If cache scenario analyzer.

Evaluates alternative cache configurations on the identical memory trace,
measures performance variations, and generates comparative explanations.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from cache_analyzer.cache import CacheConfig
from cache_analyzer.explanation import Explanation, ExplanationEngine
from cache_analyzer.simulator import CacheSimulator, SimulationResult


@dataclass
class WhatIfExperiment:
    """Results from a multi-configuration what-if analysis."""

    baseline_result: SimulationResult
    alternative_results: List[SimulationResult]
    explanations: List[Explanation]

    def to_table_data(self) -> List[Dict[str, Any]]:
        """Extract a structured tabular comparison of all configurations."""
        rows: List[Dict[str, Any]] = []

        # Baseline row
        b_cfg = self.baseline_result.config
        b_met = self.baseline_result.metrics
        rows.append({
            "Label": "BASELINE",
            "Config Name": b_cfg.name,
            "Cache Size": f"{b_cfg.cache_size // 1024} KB",
            "Block Size": f"{b_cfg.block_size} B",
            "Associativity": f"{b_cfg.associativity}-Way",
            "Policy": b_cfg.replacement_policy,
            "Hit Rate (%)": round(b_met.hit_rate, 2),
            "Hit Rate Delta": "— (Baseline)",
            "Miss Rate (%)": round(b_met.miss_rate, 2),
            "Miss Rate Delta": "— (Baseline)",
            "AMAT": round(b_met.amat, 3),
            "Compulsory": b_met.compulsory_misses,
            "Capacity": b_met.capacity_misses,
            "Conflict": b_met.conflict_misses,
            "Evictions": b_met.evictions,
        })

        for alt, exp in zip(self.alternative_results, self.explanations):
            a_cfg = alt.config
            a_met = alt.metrics
            hr_diff = a_met.hit_rate - b_met.hit_rate
            mr_diff = a_met.miss_rate - b_met.miss_rate
            rows.append({
                "Label": "ALTERNATIVE",
                "Config Name": a_cfg.name,
                "Cache Size": f"{a_cfg.cache_size // 1024} KB",
                "Block Size": f"{a_cfg.block_size} B",
                "Associativity": f"{a_cfg.associativity}-Way",
                "Policy": a_cfg.replacement_policy,
                "Hit Rate (%)": round(a_met.hit_rate, 2),
                "Hit Rate Delta": f"{hr_diff:+.2f}%",
                "Miss Rate (%)": round(a_met.miss_rate, 2),
                "Miss Rate Delta": f"{mr_diff:+.2f}%",
                "AMAT": round(a_met.amat, 3),
                "Compulsory": a_met.compulsory_misses,
                "Capacity": a_met.capacity_misses,
                "Conflict": a_met.conflict_misses,
                "Evictions": a_met.evictions,
                "Primary Reason": exp.primary_reason,
            })

        return rows

    def summary(self) -> str:
        """Formatted textual report with comparison table and explanations."""
        lines = [
            "==========================================================================",
            "CacheScope What-If Multi-Configuration Comparative Analysis",
            "==========================================================================",
        ]

        table = self.to_table_data()
        header = f"{'Configuration':<24} | {'Size':<6} | {'Assoc':<7} | {'Policy':<7} | {'Hit Rate':<10} | {'AMAT':<7} | {'Conflict':<8}"
        lines.append(header)
        lines.append("-" * len(header))

        for row in table:
            name = f"[{row['Label'][:4]}] {row['Config Name']}"
            lines.append(
                f"{name:<24} | {row['Cache Size']:<6} | {row['Associativity']:<7} | "
                f"{row['Policy']:<7} | {row['Hit Rate (%)']:>5.2f}%    | {row['AMAT']:>6.2f} | {row['Conflict']:>8}"
            )

        lines.append("==========================================================================")
        lines.append("Detailed Architectural Explanations:")
        for idx, exp in enumerate(self.explanations, 1):
            lines.append(f"\n--- Alternative #{idx}: {exp.title} ---")
            lines.append(f"Primary Cause: {exp.primary_reason}")
            lines.append(f"Narrative: {exp.detailed_narrative}")
            for ev in exp.evidence_points:
                lines.append(f"  * {ev}")

        return "\n".join(lines)


class WhatIfAnalyzer:
    """Executes parameter sweeps and synthesizes comparison reports."""

    def __init__(self):
        self.explanation_engine = ExplanationEngine()

    def run_alternatives(
        self,
        baseline_config: CacheConfig,
        alternative_configs: List[CacheConfig],
        trace: List[int],
        workload_name: str = "Trace",
    ) -> WhatIfExperiment:
        """Simulate baseline and a given list of alternative configurations on the same trace."""
        # Run baseline
        base_sim = CacheSimulator(baseline_config)
        base_res = base_sim.run(trace, workload_name=workload_name)

        alt_results: List[SimulationResult] = []
        explanations: List[Explanation] = []

        for alt_cfg in alternative_configs:
            alt_sim = CacheSimulator(alt_cfg)
            alt_res = alt_sim.run(trace, workload_name=workload_name)
            alt_results.append(alt_res)

            exp = self.explanation_engine.explain(
                base_config=baseline_config,
                base_metrics=base_res.metrics,
                alt_config=alt_cfg,
                alt_metrics=alt_res.metrics,
            )
            explanations.append(exp)

        return WhatIfExperiment(
            baseline_result=base_res,
            alternative_results=alt_results,
            explanations=explanations,
        )

    def generate_standard_alternatives(self, baseline: CacheConfig) -> List[CacheConfig]:
        """Automatically create comprehensive exploratory alternatives across all 4 architectural axes."""
        alternatives: List[CacheConfig] = []

        # Axis 1: Associativity Variations
        max_assoc = baseline.num_lines
        if baseline.associativity * 2 <= max_assoc:
            alternatives.append(baseline.clone_with(
                associativity=baseline.associativity * 2,
                name=f"{baseline.associativity * 2}-Way Associativity",
            ))

        if baseline.associativity * 4 <= max_assoc:
            alternatives.append(baseline.clone_with(
                associativity=baseline.associativity * 4,
                name=f"{baseline.associativity * 4}-Way Associativity",
            ))

        # Axis 2: Cache Size Variations (Both Smaller and Larger)
        # Reduced Cache Size (demonstrates working set pressure / capacity misses)
        if baseline.cache_size >= 2048 and (baseline.cache_size // 2) >= (baseline.block_size * baseline.associativity):
            reduced_size = baseline.cache_size // 2
            alternatives.append(baseline.clone_with(
                cache_size=reduced_size,
                name=f"0.5x Cache Size ({reduced_size // 1024}KB)",
            ))

        # Expanded Cache Size (demonstrates capacity miss reduction)
        expanded_size = baseline.cache_size * 2
        alternatives.append(baseline.clone_with(
            cache_size=expanded_size,
            name=f"2x Cache Size ({expanded_size // 1024}KB)",
        ))

        # Axis 3: Block Size Variations (Spatial Locality trade-off)
        if baseline.block_size * 2 <= (baseline.cache_size // baseline.associativity):
            alternatives.append(baseline.clone_with(
                block_size=baseline.block_size * 2,
                name=f"2x Block Size ({baseline.block_size * 2}B)",
            ))

        # Axis 4: Replacement Policies
        alt_pol = "FIFO" if baseline.replacement_policy == "LRU" else "LRU"
        alternatives.append(baseline.clone_with(
            replacement_policy=alt_pol,
            name=f"{alt_pol} Policy",
        ))

        # Optimal replacement as offline ceiling
        if baseline.replacement_policy != "OPTIMAL":
            alternatives.append(baseline.clone_with(
                replacement_policy="OPTIMAL",
                name="Optimal (Bélády)",
            ))

        return alternatives

    def run_sweep(
        self,
        baseline_config: CacheConfig,
        trace: List[int],
        workload_name: str = "Trace",
        custom_alternatives: Optional[List[CacheConfig]] = None,
    ) -> WhatIfExperiment:
        """Run an automated what-if exploration with standard or custom configurations."""
        alternatives = (
            custom_alternatives
            if custom_alternatives is not None
            else self.generate_standard_alternatives(baseline_config)
        )
        return self.run_alternatives(
            baseline_config=baseline_config,
            alternative_configs=alternatives,
            trace=trace,
            workload_name=workload_name,
        )
