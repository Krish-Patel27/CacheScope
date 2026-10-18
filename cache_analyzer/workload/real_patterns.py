"""
real_patterns.py — Authentic real-world memory access trace generators and workloads.

Simulates actual algorithmic execution and records the byte addresses
accessed by the CPU during real computing operations:
- Cache Thrashing Loop (Working set > cache capacity)
- Strided Matrix Traversal (Column-major spatial and conflict degradation)
- Direct-Mapped Pathological Conflict (Set aliasing)
- Sequential Memory Streaming (Spatial locality benchmark)
- Temporal Hotspot (80/20 Zipfian working set)
- Matrix Multiplication (GEMM: C = A * B)
- In-Place Quicksort Array Partitioning
- 2D Image Convolution / Stencil Processing
- Binary Search Lookups
- Linked List Pointer Chasing
- Interleaved Multi-Threaded Contention
"""

from __future__ import annotations
import os
import random
from typing import Dict, List, Tuple
from cache_analyzer.workload.base import WorkloadGenerator


# =========================================================================
# REAL ALGORITHMIC TRACE FUNCTIONS
# =========================================================================

def trace_cache_thrashing_loop(
    num_blocks: int = 80,
    iterations: int = 6,
    block_size: int = 64,
    base_addr: int = 0x1000,
) -> List[int]:
    """Generates a looping memory access pattern whose working set exceeds cache capacity.
    
    Default 80 blocks (5,120 Bytes) exceeds a standard 4KB (64-line) cache.
    Demonstrates working-set capacity thrashing under LRU/FIFO and the dramatic benefit
    of expanding cache size (e.g., to 8KB) or using Bélády's Optimal policy.
    """
    trace: List[int] = []
    block_addrs = [base_addr + (b * block_size) for b in range(num_blocks)]
    for _ in range(iterations):
        trace.extend(block_addrs)
    return trace


def trace_strided_column_matrix(
    rows: int = 32,
    cols: int = 32,
    element_size: int = 8,
    base_addr: int = 0x10000,
) -> List[int]:
    """Record column-major traversal of a 2D matrix (8KB total footprint).
    
    Each access jumps by row width (cols * element_size = 256 Bytes),
    wasting spatial locality and inducing severe set conflicts on power-of-two strides.
    """
    trace: List[int] = []
    for c in range(cols):
        for r in range(rows):
            addr = base_addr + (r * cols + c) * element_size
            trace.append(addr)
    return trace


def trace_direct_mapped_conflict(
    num_conflicts: int = 4,
    iterations: int = 100,
    stride: int = 4096,
    base_addr: int = 0x1000,
) -> List[int]:
    """Addresses that hash to the exact same cache set index (pathological set aliasing).
    
    In a direct-mapped cache (1-way), all addresses conflict in the same set,
    yielding 0% hit rate. In a 4-way associative cache, all addresses fit simultaneously,
    yielding a 99% hit rate. Unambiguous proof of the power of set-associativity.
    """
    conflict_addrs = [base_addr + (i * stride) for i in range(num_conflicts)]
    trace: List[int] = []
    for _ in range(iterations):
        trace.extend(conflict_addrs)
    return trace


def trace_sequential_streaming(
    count: int = 1024,
    stride: int = 4,
    base_addr: int = 0x1000,
) -> List[int]:
    """Linear traversal of contiguous memory elements (4KB total data).
    
    Demonstrates pure spatial locality. With 64-byte lines and 4-byte integers,
    1 miss occurs every 16 accesses (93.75% hit rate). When block size is doubled
    to 128 bytes, hit rate increases to 96.88%. Associativity has zero effect.
    """
    return [base_addr + (i * stride) for i in range(count)]


def trace_temporal_hotspot(
    hot_blocks: int = 32,
    cold_blocks: int = 128,
    hot_ratio: float = 0.80,
    total_accesses: int = 1000,
    block_size: int = 64,
    seed: int = 42,
    base_addr: int = 0x20000,
) -> List[int]:
    """Simulates realistic 80/20 Zipfian memory usage (e.g. database query cache).
    
    80% of accesses hit a 2KB hot working set, while 20% access a 8KB cold background pool.
    Exerts realistic pressure that highlights differences between LRU, FIFO, and LFU policies.
    """
    rng = random.Random(seed)
    hot_addrs = [base_addr + (i * block_size) for i in range(hot_blocks)]
    cold_addrs = [base_addr + ((hot_blocks + i) * block_size) for i in range(cold_blocks)]

    trace: List[int] = []
    for _ in range(total_accesses):
        if rng.random() < hot_ratio:
            trace.append(rng.choice(hot_addrs))
        else:
            trace.append(rng.choice(cold_addrs))
    return trace


def trace_matrix_multiplication(
    dim: int = 18,
    element_size: int = 8,
    base_a: int = 0x10000,
) -> List[int]:
    """Record authentic memory address accesses of a Matrix Multiplication (C = A * B).
    
    A, B, and C are dim x dim matrices of 64-bit doubles (8 bytes).
    Computes: C[i][j] += A[i][k] * B[k][j]. Footprint: 3 * dim * dim * 8 bytes (7.7 KB).
    """
    matrix_bytes = dim * dim * element_size
    base_b = base_a + matrix_bytes + 256
    base_c = base_b + matrix_bytes + 256

    trace: List[int] = []

    for i in range(dim):
        for j in range(dim):
            addr_c = base_c + (i * dim + j) * element_size
            trace.append(addr_c)

            for k in range(dim):
                addr_a = base_a + (i * dim + k) * element_size
                trace.append(addr_a)

                addr_b = base_b + (k * dim + j) * element_size
                trace.append(addr_b)

            trace.append(addr_c)

    return trace


def trace_quicksort(
    num_elements: int = 200,
    element_size: int = 8,
    base_addr: int = 0x20000,
    seed: int = 42,
) -> List[int]:
    """Record authentic memory addresses accessed by the CPU during in-place Quicksort.
    
    Traces element reads, pivot comparisons, and pairwise swaps across recursive partitions.
    """
    rng = random.Random(seed)
    arr = [rng.randint(0, 10000) for _ in range(num_elements)]
    trace: List[int] = []

    def address_of(index: int) -> int:
        return base_addr + (index * element_size)

    def quicksort_rec(low: int, high: int):
        if low < high:
            pivot = arr[high]
            trace.append(address_of(high))

            i = low - 1
            for j in range(low, high):
                trace.append(address_of(j))
                if arr[j] <= pivot:
                    i += 1
                    trace.append(address_of(i))
                    trace.append(address_of(j))
                    arr[i], arr[j] = arr[j], arr[i]
                    trace.append(address_of(i))
                    trace.append(address_of(j))

            trace.append(address_of(i + 1))
            trace.append(address_of(high))
            arr[i + 1], arr[high] = arr[high], arr[i + 1]
            trace.append(address_of(i + 1))
            trace.append(address_of(high))

            pi = i + 1
            quicksort_rec(low, pi - 1)
            quicksort_rec(pi + 1, high)

    quicksort_rec(0, num_elements - 1)
    return trace


def trace_image_convolution(
    width: int = 20,
    height: int = 20,
    kernel_dim: int = 3,
    base_src: int = 0x30000,
) -> List[int]:
    """Record real memory addresses for a 2D spatial convolution filter (e.g. 3x3 Gaussian Blur)."""
    base_dst = base_src + (width * height * 4) + 512
    trace: List[int] = []
    pad = kernel_dim // 2

    for y in range(pad, height - pad):
        for x in range(pad, width - pad):
            for ky in range(-pad, pad + 1):
                for kx in range(-pad, pad + 1):
                    src_addr = base_src + ((y + ky) * width + (x + kx)) * 4
                    trace.append(src_addr)

            dst_addr = base_dst + (y * width + x) * 4
            trace.append(dst_addr)

    return trace


def trace_binary_search(
    num_elements: int = 512,
    num_queries: int = 60,
    base_addr: int = 0x40000,
    seed: int = 42,
) -> List[int]:
    """Record memory addresses accessed while binary searching in a sorted array."""
    rng = random.Random(seed)
    trace: List[int] = []
    element_size = 4

    for _ in range(num_queries):
        target_idx = rng.randint(0, num_elements - 1)
        low = 0
        high = num_elements - 1

        while low <= high:
            mid = (low + high) // 2
            mid_addr = base_addr + (mid * element_size)
            trace.append(mid_addr)

            if mid == target_idx:
                break
            elif mid < target_idx:
                low = mid + 1
            else:
                high = mid - 1

    return trace


def trace_linked_list_traversal(
    num_nodes: int = 64,
    num_passes: int = 6,
    base_addr: int = 0x50000,
    seed: int = 42,
) -> List[int]:
    """Record memory addresses of pointer-chasing through non-contiguous heap nodes."""
    rng = random.Random(seed)
    node_size = 64
    offsets = list(range(num_nodes))
    rng.shuffle(offsets)

    trace: List[int] = []
    for _ in range(num_passes):
        for off in offsets:
            node_addr = base_addr + (off * node_size)
            trace.append(node_addr)
            trace.append(node_addr + 8)

    return trace


def trace_interleaved_threads(
    blocks_per_thread: int = 60,
    switch_burst: int = 8,
    total_accesses: int = 600,
    block_size: int = 64,
) -> List[int]:
    """Record memory access stream of two concurrent threads competing for cache lines."""
    base_thread_a = 0x60000
    base_thread_b = 0x80000

    trace: List[int] = []
    cur_thread = "A"
    step_in_thread = 0

    idx_a = 0
    idx_b = 0

    while len(trace) < total_accesses:
        if cur_thread == "A":
            addr = base_thread_a + ((idx_a % blocks_per_thread) * block_size)
            trace.append(addr)
            idx_a += 1
        else:
            addr = base_thread_b + ((idx_b % blocks_per_thread) * block_size)
            trace.append(addr)
            idx_b += 1

        step_in_thread += 1
        if step_in_thread >= switch_burst:
            step_in_thread = 0
            cur_thread = "B" if cur_thread == "A" else "A"

    return trace


# =========================================================================
# WorkloadGenerator Subclasses for Workload Registry
# =========================================================================

class LoopThrashingWorkload(WorkloadGenerator):
    """Working set larger than standard cache capacity causing LRU thrashing."""

    def __init__(self, num_blocks: int = 80, iterations: int = 6, block_size: int = 64, **kwargs):
        super().__init__(name="LOOP_THRASHING", num_blocks=num_blocks, iterations=iterations, block_size=block_size, **kwargs)
        self.num_blocks = num_blocks
        self.iterations = iterations
        self.block_size = block_size

    def generate(self) -> List[int]:
        return trace_cache_thrashing_loop(num_blocks=self.num_blocks, iterations=self.iterations, block_size=self.block_size)

    def description(self) -> str:
        return f"Cache Thrashing Loop: {self.num_blocks} blocks ({self.num_blocks * self.block_size}B) cycled {self.iterations} times."


class StridedMatrixWorkload(WorkloadGenerator):
    """Column-major 2D matrix traversal with large strided jumps."""

    def __init__(self, rows: int = 32, cols: int = 32, element_size: int = 8, **kwargs):
        super().__init__(name="STRIDED_MATRIX", rows=rows, cols=cols, element_size=element_size, **kwargs)
        self.rows = rows
        self.cols = cols
        self.element_size = element_size

    def generate(self) -> List[int]:
        return trace_strided_column_matrix(rows=self.rows, cols=self.cols, element_size=self.element_size)

    def description(self) -> str:
        return f"Strided Column-Major Matrix Traversal: {self.rows}x{self.cols} ({self.rows * self.cols * self.element_size}B)."


class ConflictAliasingWorkload(WorkloadGenerator):
    """Pathological conflict miss pattern with addresses aliasing on identical set indices."""

    def __init__(self, num_conflicts: int = 4, iterations: int = 100, stride: int = 4096, **kwargs):
        super().__init__(name="CONFLICT_ALIASING", num_conflicts=num_conflicts, iterations=iterations, stride=stride, **kwargs)
        self.num_conflicts = num_conflicts
        self.iterations = iterations
        self.stride = stride

    def generate(self) -> List[int]:
        return trace_direct_mapped_conflict(num_conflicts=self.num_conflicts, iterations=self.iterations, stride=self.stride)

    def description(self) -> str:
        return f"Direct-Mapped Conflict Aliasing: {self.num_conflicts} conflicting lines repeated {self.iterations} times."


class SequentialStreamingWorkload(WorkloadGenerator):
    """Linear sequential memory access benchmarking spatial locality."""

    def __init__(self, count: int = 1024, stride: int = 4, **kwargs):
        super().__init__(name="SEQUENTIAL_STREAMING", count=count, stride=stride, **kwargs)
        self.count = count
        self.stride = stride

    def generate(self) -> List[int]:
        return trace_sequential_streaming(count=self.count, stride=self.stride)

    def description(self) -> str:
        return f"Sequential Memory Stream: {self.count} accesses with stride {self.stride}B."


class TemporalHotspotWorkload(WorkloadGenerator):
    """80/20 Pareto/Zipfian distribution testing temporal locality and replacement policies."""

    def __init__(self, hot_blocks: int = 32, cold_blocks: int = 128, hot_ratio: float = 0.80, total_accesses: int = 1000, **kwargs):
        super().__init__(name="TEMPORAL_HOTSPOT", hot_blocks=hot_blocks, cold_blocks=cold_blocks, hot_ratio=hot_ratio, total_accesses=total_accesses, **kwargs)
        self.hot_blocks = hot_blocks
        self.cold_blocks = cold_blocks
        self.hot_ratio = hot_ratio
        self.total_accesses = total_accesses

    def generate(self) -> List[int]:
        return trace_temporal_hotspot(hot_blocks=self.hot_blocks, cold_blocks=self.cold_blocks, hot_ratio=self.hot_ratio, total_accesses=self.total_accesses)

    def description(self) -> str:
        return f"Temporal Hotspot: {self.total_accesses} accesses with {int(self.hot_ratio*100)}% on {self.hot_blocks} hot blocks."


class MatrixMultWorkload(WorkloadGenerator):
    """Matrix Multiplication (GEMM: C = A * B). Dense linear algebra with strided reads."""

    def __init__(self, dim: int = 18, element_size: int = 8, **kwargs):
        super().__init__(name="MATRIX_MULT", dim=dim, element_size=element_size, **kwargs)
        self.dim = dim
        self.element_size = element_size

    def generate(self) -> List[int]:
        return trace_matrix_multiplication(dim=self.dim, element_size=self.element_size)

    def description(self) -> str:
        return f"Real GEMM Matrix Multiplication of {self.dim}x{self.dim} double precision matrices."


class QuicksortWorkload(WorkloadGenerator):
    """In-Place Quicksort partitioning and recursive sorting trace."""

    def __init__(self, num_elements: int = 200, seed: int = 42, **kwargs):
        super().__init__(name="QUICKSORT", num_elements=num_elements, seed=seed, **kwargs)
        self.num_elements = num_elements
        self.seed = seed

    def generate(self) -> List[int]:
        return trace_quicksort(num_elements=self.num_elements, seed=self.seed)

    def description(self) -> str:
        return f"Real In-Place Quicksort on an array of {self.num_elements} elements."


class ImageConvolutionWorkload(WorkloadGenerator):
    """2D spatial image convolution stencil filtering."""

    def __init__(self, width: int = 20, height: int = 20, kernel_dim: int = 3, **kwargs):
        super().__init__(name="IMAGE_CONVOLUTION", width=width, height=height, kernel_dim=kernel_dim, **kwargs)
        self.width = width
        self.height = height
        self.kernel_dim = kernel_dim

    def generate(self) -> List[int]:
        return trace_image_convolution(width=self.width, height=self.height, kernel_dim=self.kernel_dim)

    def description(self) -> str:
        return f"Real 2D image filter convolution over a {self.width}x{self.height} pixel canvas."


class BinarySearchWorkload(WorkloadGenerator):
    """Binary Search tree/array queries."""

    def __init__(self, num_elements: int = 512, num_queries: int = 60, seed: int = 42, **kwargs):
        super().__init__(name="BINARY_SEARCH", num_elements=num_elements, num_queries=num_queries, seed=seed, **kwargs)
        self.num_elements = num_elements
        self.num_queries = num_queries
        self.seed = seed

    def generate(self) -> List[int]:
        return trace_binary_search(num_elements=self.num_elements, num_queries=self.num_queries, seed=self.seed)

    def description(self) -> str:
        return f"Real Binary Search queries ({self.num_queries} searches over {self.num_elements} sorted items)."


class LinkedListWorkload(WorkloadGenerator):
    """Linked list traversal with fragmented heap pointer chasing."""

    def __init__(self, num_nodes: int = 64, num_passes: int = 6, seed: int = 42, **kwargs):
        super().__init__(name="LINKED_LIST", num_nodes=num_nodes, num_passes=num_passes, seed=seed, **kwargs)
        self.num_nodes = num_nodes
        self.num_passes = num_passes
        self.seed = seed

    def generate(self) -> List[int]:
        return trace_linked_list_traversal(num_nodes=self.num_nodes, num_passes=self.num_passes, seed=self.seed)

    def description(self) -> str:
        return f"Real pointer-chasing across {self.num_nodes} non-contiguous heap nodes ({self.num_passes} passes)."


class ThreadContentionWorkload(WorkloadGenerator):
    """Interleaved multi-threaded memory access stream competing for cache sets."""

    def __init__(self, blocks_per_thread: int = 60, switch_burst: int = 8, total_accesses: int = 600, **kwargs):
        super().__init__(name="THREAD_CONTENTION", blocks_per_thread=blocks_per_thread, switch_burst=switch_burst, total_accesses=total_accesses, **kwargs)
        self.blocks_per_thread = blocks_per_thread
        self.switch_burst = switch_burst
        self.total_accesses = total_accesses

    def generate(self) -> List[int]:
        return trace_interleaved_threads(blocks_per_thread=self.blocks_per_thread, switch_burst=self.switch_burst, total_accesses=self.total_accesses)

    def description(self) -> str:
        return f"Real interleaved execution of 2 threads competing for shared cache sets ({self.total_accesses} accesses)."


# =========================================================================
# DATASET GENERATION ON DISK UTILITY
# =========================================================================

def generate_all_pattern_datasets(datasets_dir: str = "datasets") -> Dict[str, str]:
    """Generates authentic, real-world memory access trace files into `datasets/`.
    
    Each file represents a genuine memory access pattern with documented hardware impact.
    Returns mapping of filename -> description.
    """
    os.makedirs(datasets_dir, exist_ok=True)

    catalog: List[Tuple[str, str, List[int]]] = [
        (
            "01_sequential_streaming.trace",
            "Sequential array streaming (1,024 words, 4KB data). Tests pure spatial locality & block-size impact.",
            trace_sequential_streaming(count=1024, stride=4),
        ),
        (
            "02_strided_matrix_traversal.trace",
            "Column-major 2D matrix traversal (32x32 doubles, 8KB footprint). Stride=256B degrades spatial reuse and causes conflicts.",
            trace_strided_column_matrix(rows=32, cols=32, element_size=8),
        ),
        (
            "03_cache_thrashing_loop.trace",
            "Looping working set of 80 blocks (5.1KB) exceeding 4KB cache. Shows catastrophic capacity misses on LRU/FIFO.",
            trace_cache_thrashing_loop(num_blocks=80, iterations=6),
        ),
        (
            "04_direct_mapped_conflict.trace",
            "4 addresses hashing to exact same set index. Demonstrates 0% hit rate in 1-way vs 99% in 4-way set-associativity.",
            trace_direct_mapped_conflict(num_conflicts=4, iterations=100),
        ),
        (
            "05_temporal_hotspot_lru.trace",
            "80/20 Pareto distribution (32 hot blocks, 128 cold blocks, 1,000 accesses). Demonstrates temporal locality & eviction policies.",
            trace_temporal_hotspot(hot_blocks=32, cold_blocks=128, hot_ratio=0.80, total_accesses=1000),
        ),
        (
            "06_matrix_multiplication_gemm.trace",
            "Real GEMM (18x18 double precision matrices, 12,312 accesses). Mix of row-sequential, column-strided, and accumulator writes.",
            trace_matrix_multiplication(dim=18),
        ),
        (
            "07_quicksort_partitioning.trace",
            "Real in-place recursive Quicksort on 200 elements (6,200+ accesses). Dynamic array swapping and shrinking subarrays.",
            trace_quicksort(num_elements=200),
        ),
        (
            "08_image_spatial_convolution.trace",
            "Real 2D image convolution (20x20 image, 3x3 blur stencil, 4,840 accesses). High spatial locality across neighboring rows.",
            trace_image_convolution(width=20, height=20, kernel_dim=3),
        ),
        (
            "09_binary_search_lookups.trace",
            "Real Binary Search queries (60 queries across 512 elements). High temporal root reuse, branching memory jumps.",
            trace_binary_search(num_elements=512, num_queries=60),
        ),
        (
            "10_pointer_chasing_linkedlist.trace",
            "Real pointer chasing through 64 fragmented heap nodes (1,280 accesses). Zero spatial locality.",
            trace_linked_list_traversal(num_nodes=64, num_passes=6),
        ),
        (
            "11_multithread_contention.trace",
            "Interleaved execution of 2 threads switching every 8 operations (600 accesses). Demonstrates set contention.",
            trace_interleaved_threads(blocks_per_thread=60, switch_burst=8, total_accesses=600),
        ),
    ]

    results: Dict[str, str] = {}
    for filename, desc, trace in catalog:
        filepath = os.path.join(datasets_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# CacheScope Authentic Memory Access Trace Dataset\n")
            f.write(f"# File: {filename}\n")
            f.write(f"# Description: {desc}\n")
            f.write(f"# Total Accesses: {len(trace):,}\n")
            f.write(f"# Unique 64B Blocks: {len(set(a // 64 for a in trace)):,}\n")
            f.write(f"# Generated by: cache_analyzer.workload.real_patterns\n#\n")
            for addr in trace:
                f.write(f"0x{addr:08X}\n")
        results[filename] = desc

    return results
