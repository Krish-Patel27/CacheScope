"""Tests for replacement policies: LRU, FIFO, LFU, Random, Optimal."""

import unittest
from cache_analyzer.cache import Cache, CacheConfig
from cache_analyzer.replacement import get_policy
from cache_analyzer.replacement.optimal import OptimalPolicy


class TestPolicies(unittest.TestCase):
    def test_lru_replacement(self):
        cfg = CacheConfig(cache_size=128, block_size=64, associativity=2)
        cache = Cache(cfg)
        policy = get_policy("LRU")
        c_set = cache.sets[0]

        policy.on_insert(c_set.ways[0], way_idx=0, cache_set=c_set, tag=10, block_number=10, access_counter=1)
        policy.on_insert(c_set.ways[1], way_idx=1, cache_set=c_set, tag=20, block_number=20, access_counter=2)

        policy.on_hit(c_set.ways[0], way_idx=0, cache_set=c_set, access_counter=3)

        victim_idx, victim_line = policy.select_victim(c_set)
        self.assertEqual(victim_idx, 1)
        self.assertEqual(victim_line.tag, 20)

    def test_fifo_replacement(self):
        cfg = CacheConfig(cache_size=128, block_size=64, associativity=2)
        cache = Cache(cfg)
        policy = get_policy("FIFO")
        c_set = cache.sets[0]

        policy.on_insert(c_set.ways[0], way_idx=0, cache_set=c_set, tag=10, block_number=10, access_counter=1)
        policy.on_insert(c_set.ways[1], way_idx=1, cache_set=c_set, tag=20, block_number=20, access_counter=2)

        policy.on_hit(c_set.ways[0], way_idx=0, cache_set=c_set, access_counter=3)

        victim_idx, victim_line = policy.select_victim(c_set)
        self.assertEqual(victim_idx, 0)
        self.assertEqual(victim_line.tag, 10)

    def test_lfu_replacement(self):
        cfg = CacheConfig(cache_size=128, block_size=64, associativity=2)
        cache = Cache(cfg)
        policy = get_policy("LFU")
        c_set = cache.sets[0]

        policy.on_insert(c_set.ways[0], way_idx=0, cache_set=c_set, tag=10, block_number=10, access_counter=1)
        policy.on_insert(c_set.ways[1], way_idx=1, cache_set=c_set, tag=20, block_number=20, access_counter=2)

        policy.on_hit(c_set.ways[0], way_idx=0, cache_set=c_set, access_counter=3)
        policy.on_hit(c_set.ways[0], way_idx=0, cache_set=c_set, access_counter=4)

        victim_idx, victim_line = policy.select_victim(c_set)
        self.assertEqual(victim_idx, 1)

    def test_optimal_replacement(self):
        cfg = CacheConfig(cache_size=128, block_size=64, associativity=2)
        cache = Cache(cfg)
        policy = OptimalPolicy()
        c_set = cache.sets[0]

        policy.prepare_trace([10, 20, 30, 20, 10])

        policy.on_insert(c_set.ways[0], way_idx=0, cache_set=c_set, tag=10, block_number=10, access_counter=1)
        policy.on_insert(c_set.ways[1], way_idx=1, cache_set=c_set, tag=20, block_number=20, access_counter=2)

        victim_idx, victim_line = policy.select_victim(c_set, current_step=2)
        self.assertEqual(victim_line.block_number, 10)


if __name__ == "__main__":
    unittest.main()
