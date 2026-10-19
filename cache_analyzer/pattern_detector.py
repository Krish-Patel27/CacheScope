"""
pattern_detector.py — Memory access pattern detection and characterization.

Analyzes raw memory access traces to detect:
- Sequential access (unit stride)
- Strided access (non-unit constant stride, e.g. matrix column traversals)
- Looping behavior (periodic cycles of repeated addresses)
- Temporal locality score (working set reuse within short windows)
- Spatial locality score (clustered accesses in same/adjacent cache blocks)
- Random behavior
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter


@dataclass
class PatternReport:
    """Detailed characterization of an address stream."""

    total_accesses: int
    unique_addresses: int
    unique_blocks: int
    dominant_pattern: str            # SEQUENTIAL, STRIDED, LOOPING, LOCALITY_HEAVY, or RANDOM
    confidence: float                # 0.0 to 1.0
    temporal_locality_score: float   # 0.0 to 1.0 (higher = more temporal reuse)
    spatial_locality_score: float    # 0.0 to 1.0 (higher = more adjacent block hits)
    detected_stride: Optional[int] = None
    detected_loop_length: Optional[int] = None
    stride_distribution: Dict[int, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "total_accesses": self.total_accesses,
            "unique_addresses": self.unique_addresses,
            "unique_blocks": self.unique_blocks,
            "dominant_pattern": self.dominant_pattern,
            "confidence": round(self.confidence, 2),
            "temporal_locality_score": round(self.temporal_locality_score, 2),
            "spatial_locality_score": round(self.spatial_locality_score, 2),
            "detected_stride": self.detected_stride,
            "detected_loop_length": self.detected_loop_length,
            "recommendations": list(self.recommendations),
        }

    def summary(self) -> str:
        """Formatted textual report."""
        stride_info = f" | Stride: {self.detected_stride}B" if self.detected_stride else ""
        loop_info = f" | Loop Period: {self.detected_loop_length} accesses" if self.detected_loop_length else ""
        rec_str = "\n".join(f"  * {r}" for r in self.recommendations)
        return (
            f"=== Access Pattern Characterization ===\n"
            f"Dominant Pattern : {self.dominant_pattern} (Confidence: {self.confidence*100:.1f}%){stride_info}{loop_info}\n"
            f"Temporal Locality: {self.temporal_locality_score*100:.1f}%\n"
            f"Spatial Locality : {self.spatial_locality_score*100:.1f}%\n"
            f"Unique Addresses : {self.unique_addresses:,} (spanning {self.unique_blocks:,} blocks)\n"
            f"Recommendations  :\n{rec_str}"
        )


class AccessPatternDetector:
    """Analyzes a stream of byte addresses and infers architectural access patterns."""

    def __init__(self, default_block_size: int = 64, temporal_window: int = 16):
        self.block_size = default_block_size
        self.temporal_window = temporal_window

    def analyze(self, trace: List[int]) -> PatternReport:
        """Perform comprehensive pattern classification on address trace."""
        if not trace:
            return PatternReport(
                total_accesses=0,
                unique_addresses=0,
                unique_blocks=0,
                dominant_pattern="UNKNOWN",
                confidence=0.0,
                temporal_locality_score=0.0,
                spatial_locality_score=0.0,
                recommendations=["Empty trace provided."],
            )

        n = len(trace)
        unique_addrs = len(set(trace))
        blocks = [a // self.block_size for a in trace]
        unique_blks = len(set(blocks))

        # 1. Stride Analysis
        strides: List[int] = []
        for i in range(1, n):
            strides.append(trace[i] - trace[i - 1])

        stride_counter = Counter(strides)
        most_common_stride, most_common_stride_count = (
            stride_counter.most_common(1)[0] if strides else (0, 0)
        )
        stride_ratio = (most_common_stride_count / len(strides)) if strides else 0.0

        # 2. Spatial Locality Score: fraction of accesses within +/- 1 block of previous
        spatial_hits = 0
        for i in range(1, n):
            blk_diff = abs(blocks[i] - blocks[i - 1])
            if blk_diff <= 1:
                spatial_hits += 1
        spatial_score = (spatial_hits / (n - 1)) if n > 1 else 0.0

        # 3. Temporal Locality Score: fraction of accesses found in the last W unique accesses
        temporal_hits = 0
        window: List[int] = []
        for i, addr in enumerate(trace):
            if addr in window:
                temporal_hits += 1
            window.append(addr)
            if len(window) > self.temporal_window:
                window.pop(0)
        temporal_score = temporal_hits / n

        # 4. Looping / Periodicity Detection
        loop_length, loop_confidence = self._detect_loop_period(trace)

        # 5. Dominant Pattern Classification
        dominant = "RANDOM"
        confidence = 0.5
        recs: List[str] = []

        if loop_length is not None and loop_confidence >= 0.65:
            dominant = "LOOPING"
            confidence = loop_confidence
            working_set_blocks = len(set(blocks[:loop_length]))
            recs.append(
                f"Looping pattern detected with period of {loop_length} accesses "
                f"({working_set_blocks} cache blocks)."
            )
            recs.append(
                f"Ensure cache capacity has at least {working_set_blocks} lines "
                f"to prevent severe loop thrashing."
            )
        elif stride_ratio >= 0.70:
            if abs(most_common_stride) in (1, 2, 4, 8, self.block_size):
                dominant = "SEQUENTIAL"
                confidence = stride_ratio
                recs.append(
                    f"Strong sequential access (stride = {most_common_stride}B). "
                    f"Larger cache block sizes (e.g. 64B or 128B) will dramatically boost hit rate."
                )
            else:
                dominant = "STRIDED"
                confidence = stride_ratio
                recs.append(
                    f"Regular strided access pattern (stride = {most_common_stride}B). "
                    f"Watch out for power-of-two strides that map repeatedly to identical cache sets."
                )
        elif temporal_score >= 0.50 or spatial_score >= 0.70:
            dominant = "LOCALITY_HEAVY"
            confidence = max(temporal_score, spatial_score)
            recs.append(
                f"High locality workload: {temporal_score*100:.1f}% temporal, {spatial_score*100:.1f}% spatial."
            )
            recs.append(
                "LRU replacement policy will perform excellently here by preserving active working sets."
            )
        else:
            dominant = "RANDOM"
            confidence = max(0.5, 1.0 - max(temporal_score, spatial_score))
            recs.append(
                "Workload exhibits random or near-uniform access patterns with low reuse."
            )
            recs.append(
                "Increasing associativity or cache size may have diminishing returns; consider larger capacity."
            )

        return PatternReport(
            total_accesses=n,
            unique_addresses=unique_addrs,
            unique_blocks=unique_blks,
            dominant_pattern=dominant,
            confidence=confidence,
            temporal_locality_score=temporal_score,
            spatial_locality_score=spatial_score,
            detected_stride=most_common_stride if stride_ratio >= 0.5 else None,
            detected_loop_length=loop_length,
            stride_distribution=dict(stride_counter.most_common(5)),
            recommendations=recs,
        )

    def _detect_loop_period(self, trace: List[int]) -> Tuple[Optional[int], float]:
        """Detect recurring periods in the trace using autocorrelation / cycle matching."""
        n = len(trace)
        if n < 8:
            return None, 0.0

        max_check = min(256, n // 2)
        best_period = None
        best_matches = 0

        for period in range(2, max_check + 1):
            matches = 0
            comparisons = n - period
            for i in range(comparisons):
                if trace[i] == trace[i + period]:
                    matches += 1
            score = matches / comparisons
            if score >= 0.75 and matches > best_matches:
                best_matches = matches
                best_period = period

        if best_period is not None:
            conf = best_matches / (n - best_period)
            return best_period, conf

        return None, 0.0
