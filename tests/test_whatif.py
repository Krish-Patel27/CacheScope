"""Tests for What-If scenario analyzer and Explanation Engine."""

import unittest
from cache_analyzer.cache import CacheConfig
from cache_analyzer.whatif import WhatIfAnalyzer
from cache_analyzer.pattern_detector import AccessPatternDetector


class TestWhatIf(unittest.TestCase):
    def test_whatif_sweep_and_explanation(self):
        # 256B cache, 64B block, 1-way -> 4 lines, 4 sets
        baseline = CacheConfig(cache_size=256, block_size=64, associativity=1, replacement_policy="LRU")
        analyzer = WhatIfAnalyzer()

        # In 4 sets: block 0 (addr 0) and block 4 (addr 256) both map to set 0 (0 % 4 == 0, 4 % 4 == 0)
        trace = [0, 256, 0, 256]
        experiment = analyzer.run_sweep(baseline, trace, workload_name="PingPongConflict")

        self.assertGreater(experiment.baseline_result.metrics.conflict_misses, 0)
        self.assertGreaterEqual(len(experiment.alternative_results), 2)
        self.assertEqual(len(experiment.explanations), len(experiment.alternative_results))

        two_way_res = None
        for res in experiment.alternative_results:
            if res.config.associativity >= 2 and res.config.cache_size == 256:
                two_way_res = res
                break

        if two_way_res:
            self.assertEqual(two_way_res.metrics.conflict_misses, 0)

    def test_pattern_detector(self):
        detector = AccessPatternDetector(default_block_size=64)

        # 1. Sequential trace
        seq_trace = [i * 4 for i in range(100)]
        report = detector.analyze(seq_trace)
        self.assertEqual(report.dominant_pattern, "SEQUENTIAL")

        # 2. Looping trace
        loop_cycle = [0x1000 + i * 64 for i in range(8)]
        loop_trace = loop_cycle * 5
        report = detector.analyze(loop_trace)
        self.assertEqual(report.dominant_pattern, "LOOPING")
        self.assertEqual(report.detected_loop_length, 8)


if __name__ == "__main__":
    unittest.main()
