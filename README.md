# ⚡ CacheScope — Intelligent Cache Behavior Analyzer & Optimizer

> **CacheScope** is a modular, extensible computer-architecture analysis platform built in Python. Rather than simply simulating whether memory accesses hit or miss, CacheScope classifies 3C misses, characterizes access patterns, simulates what-if architectural alternatives, and **explains WHY cache behavior changed**.

---

## 🌟 Key Features

1. **Flexible Cache Geometry & Organizations**:
   - Direct-Mapped caches (1-way).
   - Set-Associative caches ($N$-way).
   - Fully Associative caches ($N$ lines, 1 set).
   - Automated address decomposition: Tag, Set Index, Offset, Block Number.

2. **Pluggable Replacement Policies**:
   - **LRU** (Least Recently Used)
   - **FIFO** (First In, First Out)
   - **LFU** (Least Frequently Used with tie-breaking)
   - **Random** (Pseudorandom eviction with reproducible seeds)
   - **Optimal (Bélády's MIN)** (Theoretical offline upper-bound)

3. **Academic 3C Miss Classification**:
   - **Compulsory (Cold) Misses**: First-time referenced memory blocks.
   - **Capacity Misses**: Working set exceeds cache capacity (misses even in an equal-sized fully-associative cache).
   - **Conflict Misses**: Set collisions due to limited ways where total cache space was still available.

4. **Memory Access Pattern Detector**:
   - Detects **Sequential**, **Strided**, **Looping**, **Locality-Heavy**, and **Random** access streams.
   - Computes **Temporal Locality** and **Spatial Locality** scores.
   - Recommends concrete cache geometry adjustments (e.g. minimum lines to avoid loop thrashing).

5. **What-If Scenario Analyzer & "Why" Engine**:
   - Sweeps alternative configurations (Size, Associativity, Block Size, Policy) on the **exact same trace**.
   - Generates architectural explanations explaining the physical causes behind metric shifts.

6. **Dual User Interfaces**:
   - **Interactive Web Dashboard** (Streamlit + Plotly): Live sliders, set heatmap, step-by-step inspector.
   - **Command-Line Interface (CLI)**: Interactive wizard, flags, ASCII heatmaps, database storage, and chart export.

---

## 📁 Project Architecture

The codebase is organized cleanly to make ongoing modifications straightforward:

```
Python_Project/
├── app.py                     # Streamlit Interactive Web Dashboard
├── run_web.py                 # Convenience launcher for Web UI
├── run_cli.py                 # Convenience launcher for CLI
├── requirements.txt           # Python package requirements
├── cachescope.db              # SQLite experiment database (auto-created)
├── sample_traces/             # Sample benchmark traces (.txt, .csv, .trace)
│   ├── simple_loop.txt
│   ├── matrix_sample.csv
│   └── valgrind_sample.trace
├── tests/                     # Unit test suite (13 automated tests)
│   ├── test_cache.py
│   ├── test_policies.py
│   ├── test_simulator.py
│   └── test_whatif.py
└── cache_analyzer/            # Core package
    ├── __init__.py            # Clean public API imports
    ├── cache.py               # CacheLine, CacheSet, CacheConfig, Cache data structures
    ├── simulator.py           # Simulation pipeline & event logging
    ├── metrics.py             # 3C classification, AMAT, set utilization metrics
    ├── pattern_detector.py    # Access pattern detection & recommendations
    ├── whatif.py              # Multi-configuration scenario evaluator
    ├── explanation.py         # Pedagogical "Why" explanation engine
    ├── visualization.py       # ASCII heatmaps, bar charts, Matplotlib figures
    ├── database.py            # SQLite storage & CSV/JSON export
    ├── replacement/           # Pluggable replacement policies
    │   ├── __init__.py        # Policy registry & @register_policy decorator
    │   ├── base.py            # ReplacementPolicy ABC
    │   ├── lru.py
    │   ├── fifo.py
    │   ├── lfu.py
    │   ├── random_policy.py
    │   └── optimal.py
    └── workload/              # Pluggable trace generators & loaders
        ├── __init__.py        # Workload registry & @register_workload decorator
        ├── base.py            # WorkloadGenerator ABC
        ├── sequential.py
        ├── random_workload.py
        ├── loop.py
        ├── locality.py
        ├── matrix.py
        └── trace_loader.py    # Loads .txt, .csv, and Dinero/Valgrind traces
```

---

## 🚀 Quick Start

### 1. Launch the Interactive Web Dashboard
```bash
streamlit run app.py
# Or using the launcher:
python run_web.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 2. Run the Command-Line Interface (CLI)

**Interactive Menu Wizard:**
```bash
python run_cli.py -i
```

**Direct Command-Line Execution:**
```bash
# Run 4KB Direct-Mapped Cache on Locality Workload with What-If Analysis and Heatmap
python run_cli.py --cache-size 4096 --block-size 64 --associativity 1 --policy LRU --workload LOCALITY --what-if --heatmap

# Run with a custom trace file and save visual dashboard PNG
python run_cli.py --trace-file sample_traces/simple_loop.txt --cache-size 1024 --block-size 64 --associativity 2 --what-if --save-chart dashboard.png --save-db
```

### 3. Run the Unit Test Suite
```bash
python -m unittest discover tests
```

---

## 🛠️ Developer Guide: How to Extend the Project

CacheScope was engineered specifically for **easy customization and future modifications**:

### A. How to Add a New Replacement Policy
You do **not** need to touch existing policies. Simply create a subclass and decorate it:

```python
# In cache_analyzer/replacement/my_policy.py (or any new file)
from cache_analyzer.replacement import ReplacementPolicy, register_policy

@register_policy("MY_POLICY")
class MyCustomPolicy(ReplacementPolicy):
    def select_victim(self, cache_set, **kwargs):
        # Pick which CacheLine in cache_set.ways to evict
        # Return tuple of (way_index, line)
        victim_idx = 0
        return victim_idx, cache_set.ways[victim_idx]

    def on_hit(self, line, way_idx, cache_set, access_counter, **kwargs):
        # Optional: update custom metadata on hits
        pass
```
*It is automatically available in the CLI, Web UI, and What-If sweeps!*

---

### B. How to Add a New Workload Generator
```python
# In cache_analyzer/workload/my_workload.py
from cache_analyzer.workload import WorkloadGenerator, register_workload

@register_workload("STRIDED_CLUSTER")
class StridedClusterWorkload(WorkloadGenerator):
    def __init__(self, start=0, count=256, **kwargs):
        super().__init__(name="STRIDED_CLUSTER", **kwargs)
        self.start = start
        self.count = count

    def generate(self) -> list[int]:
        # Return a list of integer byte memory addresses
        return [self.start + (i * 128) for i in range(self.count)]
```

---

### C. How to Modify or Add Explanation Rules
Explanations are synthesized in [`cache_analyzer/explanation.py`](cache_analyzer/explanation.py).
To add custom rules or modify narrative text, edit `_synthesize_narrative()`:
- Inspect `param_deltas` (e.g. `cache_size`, `associativity`, `block_size`, `replacement_policy`).
- Inspect `metric_deltas` (e.g. `hit_rate_diff`, `conflict_diff`, `capacity_diff`, `amat_diff`).
- Return `(title, primary_reason, detailed_narrative)`.

---

## 📐 Cache Geometry & Formula Reference

Given byte address $A$, cache size $C$, block size $B$, and associativity $W$:

| Metric / Parameter | Formula |
| :--- | :--- |
| **Total Cache Lines ($L$)** | $L = C / B$ |
| **Total Sets ($S$)** | $S = L / W$ |
| **Block Number ($Blk$)** | $Blk = \lfloor A / B \rfloor$ |
| **Block Offset ($Off$)** | $Off = A \pmod B$ |
| **Set Index ($Idx$)** | $Idx = Blk \pmod S$ |
| **Tag ($T$)** | $T = \lfloor Blk / S \rfloor$ |
| **Offset Bits** | $\log_2(B)$ |
| **Set Index Bits** | $\log_2(S)$ |
| **Tag Bits** | $\text{Address Bits} - \text{Index Bits} - \text{Offset Bits}$ |
| **Hit Rate** | $(\text{Hits} / \text{Total Accesses}) \times 100\%$ |
| **Miss Rate** | $(\text{Misses} / \text{Total Accesses}) \times 100\%$ |
| **AMAT** | $\text{Hit Time} + (\text{Miss Rate} \times \text{Miss Penalty})$ |

---

## 📄 License
Educational & Open Source Project built for computer architecture exploration.
