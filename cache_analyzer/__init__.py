"""
CacheScope — Intelligent Cache Behavior Analyzer & Optimizer

A modular, extensible Python-based cache-memory analysis and optimization framework.
Simulates cache behavior, classifies misses, detects access patterns,
visualizes set utilization, runs what-if experiments, and explains why results changed.
"""

from cache_analyzer.cache import Cache, CacheConfig, CacheLine, CacheSet
from cache_analyzer.simulator import CacheSimulator, AccessEvent, SimulationResult
from cache_analyzer.replacement import get_policy, available_policies, register_policy
from cache_analyzer.workload import get_workload, available_workloads, register_workload, TraceLoader
from cache_analyzer.metrics import calculate_metrics, classify_misses, CacheMetrics
from cache_analyzer.pattern_detector import AccessPatternDetector, PatternReport
from cache_analyzer.whatif import WhatIfAnalyzer, WhatIfExperiment
from cache_analyzer.explanation import ExplanationEngine
from cache_analyzer.visualization import Visualizer
from cache_analyzer.database import CacheDatabase

__version__ = "1.0.0"
__all__ = [
    "Cache",
    "CacheConfig",
    "CacheLine",
    "CacheSet",
    "CacheSimulator",
    "AccessEvent",
    "SimulationResult",
    "get_policy",
    "available_policies",
    "register_policy",
    "get_workload",
    "available_workloads",
    "register_workload",
    "TraceLoader",
    "calculate_metrics",
    "classify_misses",
    "CacheMetrics",
    "AccessPatternDetector",
    "PatternReport",
    "WhatIfAnalyzer",
    "WhatIfExperiment",
    "ExplanationEngine",
    "Visualizer",
    "CacheDatabase",
]
