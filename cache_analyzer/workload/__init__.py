"""
workload — Pluggable memory-access trace generator framework.

Supports both synthetic trace generators and real algorithmic execution tracers:
- Real Access Patterns:
  - LOOP_THRASHING (Capacity pressure & thrashing)
  - STRIDED_MATRIX (Spatial breakdown & conflict aliasing)
  - CONFLICT_ALIASING (Pathological direct-mapped conflicts)
  - SEQUENTIAL_STREAMING (Spatial locality & block-size sensitivity)
  - TEMPORAL_HOTSPOT (80/20 working set & policy sensitivity)
  - MATRIX_MULT (GEMM)
  - QUICKSORT (In-place array partitioning)
  - IMAGE_CONVOLUTION (2D spatial filtering)
  - BINARY_SEARCH (Search tree queries)
  - LINKED_LIST (Fragmented pointer-chasing)
  - THREAD_CONTENTION (Interleaved multi-core threads)
- Legacy synthetic generators: LOCALITY, SEQUENTIAL, LOOP, RANDOM, MATRIX
- Custom file loader: TRACE_LOADER
"""

from typing import Callable, Dict, List, Type
from cache_analyzer.workload.base import WorkloadGenerator
from cache_analyzer.workload.sequential import SequentialWorkload
from cache_analyzer.workload.random_workload import RandomWorkload
from cache_analyzer.workload.loop import LoopWorkload
from cache_analyzer.workload.locality import LocalityWorkload
from cache_analyzer.workload.matrix import MatrixWorkload
from cache_analyzer.workload.trace_loader import TraceLoader
from cache_analyzer.workload.real_patterns import (
    LoopThrashingWorkload,
    StridedMatrixWorkload,
    ConflictAliasingWorkload,
    SequentialStreamingWorkload,
    TemporalHotspotWorkload,
    MatrixMultWorkload,
    QuicksortWorkload,
    ImageConvolutionWorkload,
    BinarySearchWorkload,
    LinkedListWorkload,
    ThreadContentionWorkload,
    generate_all_pattern_datasets,
)

WORKLOAD_REGISTRY: Dict[str, Type[WorkloadGenerator]] = {}


def register_workload(name: str) -> Callable[[Type[WorkloadGenerator]], Type[WorkloadGenerator]]:
    """Decorator to register a custom workload in the global registry."""
    def decorator(cls: Type[WorkloadGenerator]) -> Type[WorkloadGenerator]:
        key = name.strip().upper()
        WORKLOAD_REGISTRY[key] = cls
        return cls
    return decorator


# Register built-in synthetic workloads
register_workload("SEQUENTIAL")(SequentialWorkload)
register_workload("RANDOM")(RandomWorkload)
register_workload("LOOP")(LoopWorkload)
register_workload("LOCALITY")(LocalityWorkload)
register_workload("MATRIX")(MatrixWorkload)
register_workload("TRACE_LOADER")(TraceLoader)

# Register real algorithmic workloads
register_workload("LOOP_THRASHING")(LoopThrashingWorkload)
register_workload("STRIDED_MATRIX")(StridedMatrixWorkload)
register_workload("CONFLICT_ALIASING")(ConflictAliasingWorkload)
register_workload("SEQUENTIAL_STREAMING")(SequentialStreamingWorkload)
register_workload("TEMPORAL_HOTSPOT")(TemporalHotspotWorkload)
register_workload("MATRIX_MULT")(MatrixMultWorkload)
register_workload("QUICKSORT")(QuicksortWorkload)
register_workload("IMAGE_CONVOLUTION")(ImageConvolutionWorkload)
register_workload("BINARY_SEARCH")(BinarySearchWorkload)
register_workload("LINKED_LIST")(LinkedListWorkload)
register_workload("THREAD_CONTENTION")(ThreadContentionWorkload)


def get_workload(name: str, **kwargs) -> WorkloadGenerator:
    """Instantiate a workload generator by name."""
    key = name.strip().upper()
    if key not in WORKLOAD_REGISTRY:
        raise ValueError(
            f"Unknown workload '{name}'. "
            f"Available workloads: {list(WORKLOAD_REGISTRY.keys())}"
        )
    return WORKLOAD_REGISTRY[key](**kwargs)


def available_workloads() -> List[str]:
    """Return sorted list of all registered workload generator names."""
    return sorted(WORKLOAD_REGISTRY.keys())
