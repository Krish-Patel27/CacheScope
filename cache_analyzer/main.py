"""
main.py — Main Command-Line Interface and Entry Point for CacheScope.

Accepts configuration parameters, runs workloads, executes what-if experiments,
analyzes access patterns, and presents architectural explanations.
"""

from __future__ import annotations
import argparse
import os
import sys

# Ensure project root is in sys.path when executed directly as a script
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from typing import List, Optional
from cache_analyzer.cache import CacheConfig
from cache_analyzer.database import CacheDatabase
from cache_analyzer.metrics import CacheMetrics
from cache_analyzer.pattern_detector import AccessPatternDetector
from cache_analyzer.replacement import available_policies
from cache_analyzer.simulator import CacheSimulator, SimulationResult
from cache_analyzer.visualization import Visualizer
from cache_analyzer.whatif import WhatIfAnalyzer
from cache_analyzer.workload import available_workloads, get_workload, TraceLoader, WORKLOAD_REGISTRY


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="CacheScope",
        description="Intelligent Cache Behavior Analyzer & Optimizer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Core Cache Geometry
    c_group = parser.add_argument_group("Cache Architecture Configuration")
    c_group.add_argument("--cache-size", type=int, default=4096, help="Total cache capacity in bytes (e.g. 4096 for 4KB)")
    c_group.add_argument("--block-size", type=int, default=64, help="Block / line size in bytes (e.g. 64)")
    c_group.add_argument("--associativity", type=int, default=1, help="Ways per set: 1=direct-mapped, 2/4/8=set-assoc, 0=fully-assoc")
    c_group.add_argument("--policy", type=str, default="LRU", choices=available_policies(), help="Replacement policy")
    c_group.add_argument("--hit-time", type=float, default=1.0, help="L1 hit time in cycles")
    c_group.add_argument("--miss-penalty", type=float, default=100.0, help="Main memory miss penalty in cycles")

    # Workload / Trace Options
    w_group = parser.add_argument_group("Workload & Trace Options")
    w_group.add_argument("--workload", type=str, default="LOCALITY", help=f"Workload generator: {available_workloads()} or 'trace_file'")
    w_group.add_argument("--trace-file", type=str, default=None, help="Path to custom trace file (.txt, .csv, .trace)")
    w_group.add_argument("--count", type=int, default=256, help="Number of memory accesses to generate")

    # Features
    f_group = parser.add_argument_group("Analysis Features")
    f_group.add_argument("--what-if", action="store_true", help="Run multi-configuration what-if comparison suite")
    f_group.add_argument("--detect-patterns", action="store_true", help="Run access pattern detector")
    f_group.add_argument("--heatmap", action="store_true", help="Display ASCII set utilization heatmap")
    f_group.add_argument("--show-state", action="store_true", help="Display final resident cache lines table")
    f_group.add_argument("--save-chart", type=str, default=None, help="Export Matplotlib visual dashboard PNG to given path")
    f_group.add_argument("--save-db", action="store_true", help="Save experiment to SQLite database")
    f_group.add_argument("--export-csv", type=str, default=None, help="Export results to CSV file")
    f_group.add_argument("--export-json", type=str, default=None, help="Export results to JSON file")
    f_group.add_argument("-i", "--interactive", action="store_true", help="Start interactive CLI menu wizard")

    return parser


def load_trace(args) -> Tuple[List[int], str]:
    """Resolve trace from custom file or built-in workload generator."""
    if args.trace_file:
        loader = TraceLoader(filepath=args.trace_file)
        trace = loader.generate()
        name = f"FileTrace({os.path.basename(args.trace_file)})"
        return trace, name

    wk_name = args.workload.upper()
    if wk_name in WORKLOAD_REGISTRY:
        try:
            gen = get_workload(wk_name, count=args.count)
        except TypeError:
            gen = get_workload(wk_name)
    else:
        # Default LOCALITY
        gen = get_workload("LOCALITY", count=args.count)

    trace = gen.generate()
    return trace, gen.name


def interactive_menu():
    """Interactive text menu for user-guided exploration."""
    print("=" * 60)
    print("      CacheScope — Interactive Cache Behavior Analyzer      ")
    print("=" * 60)

    try:
        size_str = input("Cache Size in Bytes (default 4096 = 4KB): ").strip()
        cache_size = int(size_str) if size_str else 4096

        block_str = input("Block Size in Bytes (default 64): ").strip()
        block_size = int(block_str) if block_str else 64

        assoc_str = input("Associativity (1=Direct, 2/4/8=Set-Assoc, 0=Fully-Assoc, default 1): ").strip()
        associativity = int(assoc_str) if assoc_str else 1

        print(f"Available Policies: {', '.join(available_policies())}")
        pol_str = input("Replacement Policy (default LRU): ").strip()
        policy = pol_str.upper() if pol_str else "LRU"

        print(f"\nAvailable Workloads: {', '.join(available_workloads())}")
        wk_str = input("Workload (default LOCALITY): ").strip()
        workload = wk_str.upper() if wk_str else "LOCALITY"

        count_str = input("Access Count (default 256): ").strip()
        count = int(count_str) if count_str else 256

        what_if_str = input("Run What-If Analysis? (y/n, default y): ").strip().lower()
        run_what_if = what_if_str != "n"

        config = CacheConfig(
            cache_size=cache_size,
            block_size=block_size,
            associativity=associativity,
            replacement_policy=policy,
            name="InteractiveConfig",
        )

        args = argparse.Namespace(
            cache_size=cache_size,
            block_size=block_size,
            associativity=associativity,
            policy=policy,
            hit_time=1.0,
            miss_penalty=100.0,
            workload=workload,
            trace_file=None,
            count=count,
            what_if=run_what_if,
            detect_patterns=True,
            heatmap=True,
            show_state=False,
            save_chart=None,
            save_db=False,
            export_csv=None,
            export_json=None,
        )
        run_cli_with_args(args)
    except KeyboardInterrupt:
        print("\nExiting CacheScope.")
        sys.exit(0)


def run_cli_with_args(args):
    """Execute analysis based on command-line arguments."""
    config = CacheConfig(
        cache_size=args.cache_size,
        block_size=args.block_size,
        associativity=args.associativity,
        replacement_policy=args.policy,
        hit_time=args.hit_time,
        miss_penalty=args.miss_penalty,
        name=f"Config_{args.cache_size//1024}KB_{args.associativity}way",
    )

    print("\n" + "=" * 65)
    print(f" CacheScope: {config.summary()}")
    print("=" * 65)

    trace, wk_name = load_trace(args)
    print(f"Loaded {len(trace):,} accesses for workload '{wk_name}'.")

    # Access Pattern Detector
    if args.detect_patterns:
        detector = AccessPatternDetector(default_block_size=config.block_size)
        pat_report = detector.analyze(trace)
        print("\n" + pat_report.summary())

    # Baseline Simulation Run
    sim = CacheSimulator(config)
    result = sim.run(trace, workload_name=wk_name)
    print("\n" + result.summary())

    # Heatmap
    if args.heatmap:
        print("\n" + Visualizer.render_ascii_heatmap(result.metrics.set_access_counts))

    # Show Cache State
    if args.show_state:
        print("\n" + Visualizer.render_cache_state_table(sim.cache, limit_sets=32))

    # Matplotlib Chart Export
    if args.save_chart:
        chart_ok = Visualizer.save_matplotlib_dashboard(result, args.save_chart)
        if chart_ok:
            print(f"\n[Chart Saved] Multi-panel analysis dashboard saved to: {args.save_chart}")

    # What-If Analysis
    if args.what_if:
        print("\n" + "=" * 70)
        print(" Running What-If Multi-Configuration Comparative Analysis...")
        print("=" * 70)
        whatif_analyzer = WhatIfAnalyzer()
        experiment = whatif_analyzer.run_sweep(config, trace, workload_name=wk_name)
        print("\n" + experiment.summary())

        if args.save_chart:
            wf_chart_path = "whatif_comparison.png"
            Visualizer.save_whatif_comparison_chart(experiment, wf_chart_path)
            print(f"[Chart Saved] What-If comparison chart saved to: {wf_chart_path}")

        if args.save_db:
            db = CacheDatabase()
            exp_id = db.save_whatif(experiment, f"WhatIf_{wk_name}_{config.name}")
            print(f"[Database] What-If experiment saved to cachescope.db with ID: {exp_id}")
    elif args.save_db:
        db = CacheDatabase()
        exp_id = db.save_simulation(result)
        print(f"[Database] Simulation result saved to cachescope.db with ID: {exp_id}")

    # Exports
    if args.export_json:
        db = CacheDatabase()
        exp_id = db.save_simulation(result)
        db.export_to_json(exp_id, args.export_json)
        print(f"[Export] Saved JSON report to: {args.export_json}")

    if args.export_csv:
        db = CacheDatabase()
        exp_id = db.save_simulation(result)
        db.export_to_csv(exp_id, args.export_csv)
        print(f"[Export] Saved CSV metrics to: {args.export_csv}")

    print("\nSimulation and analysis completed successfully.")


def main():
    parser = build_parser()
    args = parser.parse_args()

    # If run with no CLI arguments, open interactive menu
    if len(sys.argv) == 1 or args.interactive:
        interactive_menu()
    else:
        run_cli_with_args(args)


if __name__ == "__main__":
    main()
