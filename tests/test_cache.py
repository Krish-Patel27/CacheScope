"""Tests for CacheConfig geometry and Cache data structures."""

import unittest
from cache_analyzer.cache import Cache, CacheConfig


class TestCacheGeometry(unittest.TestCase):
    def test_direct_mapped_geometry(self):
        # 4 KB cache, 64 B blocks, 1-way associativity (Section 11 in spec)
        cfg = CacheConfig(cache_size=4096, block_size=64, associativity=1, address_bits=32)
        self.assertEqual(cfg.num_lines, 64)
        self.assertEqual(cfg.num_sets, 64)
        self.assertEqual(cfg.offset_bits, 6)   # 2^6 = 64
        self.assertEqual(cfg.index_bits, 6)    # 2^6 = 64 sets
        self.assertEqual(cfg.tag_bits, 20)     # 32 - 6 - 6
        self.assertTrue(cfg.is_direct_mapped)
        self.assertFalse(cfg.is_fully_associative)

        # Address 100 -> block 1, offset 36
        self.assertEqual(cfg.block_number(100), 1)
        self.assertEqual(cfg.offset(100), 36)
        self.assertEqual(cfg.set_index(1), 1)
        self.assertEqual(cfg.tag(1), 0)

    def test_set_associative_geometry(self):
        # 256 B cache, 64 B blocks, 2-way associativity (Section 12 in spec)
        cfg = CacheConfig(cache_size=256, block_size=64, associativity=2, address_bits=32)
        self.assertEqual(cfg.num_lines, 4)
        self.assertEqual(cfg.num_sets, 2)
        self.assertEqual(cfg.offset_bits, 6)
        self.assertEqual(cfg.index_bits, 1)   # 2 sets -> 1 bit
        self.assertEqual(cfg.tag_bits, 25)

        # Blocks 0, 2, 4 map to set 0
        self.assertEqual(cfg.set_index(0), 0)
        self.assertEqual(cfg.set_index(2), 0)
        self.assertEqual(cfg.set_index(4), 0)

        # Blocks 1, 3, 5 map to set 1
        self.assertEqual(cfg.set_index(1), 1)
        self.assertEqual(cfg.set_index(3), 1)
        self.assertEqual(cfg.set_index(5), 1)

    def test_fully_associative_geometry(self):
        cfg = CacheConfig(cache_size=1024, block_size=64, associativity=0)
        self.assertEqual(cfg.num_lines, 16)
        self.assertEqual(cfg.num_sets, 1)
        self.assertTrue(cfg.is_fully_associative)
        self.assertEqual(cfg.associativity, 16)

    def test_cache_lookup_and_reset(self):
        cfg = CacheConfig(cache_size=256, block_size=64, associativity=1)
        cache = Cache(cfg)
        self.assertEqual(len(cache.sets), 4)
        self.assertEqual(cache.access_counter, 0)

        cache.tick()
        self.assertEqual(cache.access_counter, 1)

        cache.reset()
        self.assertEqual(cache.access_counter, 0)


if __name__ == "__main__":
    unittest.main()
