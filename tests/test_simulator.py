"""Tests for CacheSimulator, 3C miss classification, and AMAT."""

import unittest
from cache_analyzer.cache import CacheConfig
from cache_analyzer.simulator import CacheSimulator


class TestSimulator(unittest.TestCase):
    def test_simulation_hit_miss(self):
        # 4 lines total, direct mapped
        cfg = CacheConfig(cache_size=256, block_size=64, associativity=1)
        sim = CacheSimulator(cfg)

        trace = [0, 4, 64, 0]
        result = sim.run(trace)

        self.assertEqual(result.metrics.total_accesses, 4)
        self.assertEqual(result.metrics.hits, 2)
        self.assertEqual(result.metrics.misses, 2)
        self.assertEqual(result.metrics.hit_rate, 50.0)
        self.assertEqual(result.metrics.compulsory_misses, 2)
        self.assertEqual(result.metrics.conflict_misses, 0)
        self.assertEqual(result.metrics.capacity_misses, 0)

    def test_conflict_vs_capacity_misses(self):
        cfg = CacheConfig(cache_size=128, block_size=64, associativity=1)
        sim = CacheSimulator(cfg)

        trace = [0, 128, 0]
        result = sim.run(trace)

        self.assertEqual(result.metrics.total_accesses, 3)
        self.assertEqual(result.metrics.compulsory_misses, 2)
        self.assertEqual(result.metrics.conflict_misses, 1)
        self.assertEqual(result.metrics.capacity_misses, 0)

    def test_amat_calculation(self):
        cfg = CacheConfig(cache_size=256, block_size=64, associativity=1, hit_time=1.0, miss_penalty=100.0)
        sim = CacheSimulator(cfg)

        res = sim.run([0, 0])
        self.assertAlmostEqual(res.metrics.amat, 51.0, places=2)


if __name__ == "__main__":
    unittest.main()
