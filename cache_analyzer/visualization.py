"""
visualization.py — Visualization, heatmaps, and graphical charting for CacheScope.

Features:
- Set Access Heatmap (ASCII block heatmaps for terminal & Matplotlib heatmap figures)
- Miss Category Breakdown Bar Charts (Compulsory, Capacity, Conflict)
- What-If Comparison Charts (Hit rate, Misses, AMAT across configurations)
- Step-by-Step Cache State Viewer (displays resident blocks in all sets & ways)
"""

from __future__ import annotations
import math
import os
from typing import Any, Dict, List, Optional, Tuple
from cache_analyzer.cache import Cache
from cache_analyzer.metrics import CacheMetrics
from cache_analyzer.simulator import AccessEvent, SimulationResult
from cache_analyzer.whatif import WhatIfExperiment


class Visualizer:
    """Generates ASCII terminal charts and Matplotlib visual figures."""

    @staticmethod
    def render_ascii_heatmap(set_access_counts: List[int], columns: int = 16) -> str:
        """Render a terminal-friendly ASCII intensity heatmap for cache set utilization."""
        if not set_access_counts:
            return "No set data to visualize."

        max_val = max(set_access_counts) if set_access_counts else 0
        if max_val == 0:
            intensity_chars = "." * len(set_access_counts)
            return f"All sets had 0 accesses.\n[{intensity_chars}]"

        # ASCII intensity gradient compatible with all Windows/Linux terminal encodings
        shades = [".", ":", "+", "#", "@"]

        lines = [
            f"Set Access Heatmap ({len(set_access_counts)} sets, max={max_val} accesses):",
            "Legend: [. : 0%] [: : 1-25%] [+ : 26-50%] [# : 51-75%] [@ : 76-100%]",
            "-" * (columns * 2 + 5),
        ]

        row = []
        for idx, count in enumerate(set_access_counts):
            ratio = count / max_val
            shade_idx = min(len(shades) - 1, int(ratio * (len(shades) - 1)))
            char = shades[shade_idx]
            row.append(char)

            if (idx + 1) % columns == 0 or idx == len(set_access_counts) - 1:
                start_set = idx - len(row) + 1
                lines.append(f"Sets {start_set:>3}-{idx:>3}: {' '.join(row)}")
                row = []

        return "\n".join(lines)

    @staticmethod
    def render_ascii_bar_chart(data: Dict[str, float], title: str = "Bar Chart", max_width: int = 40) -> str:
        """Render a horizontal ASCII bar chart."""
        lines = [f"=== {title} ==="]
        max_val = max(data.values()) if data else 1.0
        if max_val == 0:
            max_val = 1.0

        for label, val in data.items():
            bar_len = int((val / max_val) * max_width)
            bar = "#" * bar_len
            lines.append(f"{label:<20} | {bar:<{max_width}} {val:.2f}")

        return "\n".join(lines)

    @staticmethod
    def render_cache_state_table(cache: Cache, limit_sets: int = 32) -> str:
        """Render a tabular ASCII snapshot of cache lines, tags, and valid bits."""
        lines = [
            f"=== Cache Resident State ({min(len(cache.sets), limit_sets)} of {len(cache.sets)} Sets Shown) ===",
            f"{'Set':<5} | " + " | ".join(f"{'Way ' + str(w):<12}" for w in range(cache.config.associativity)),
            "-" * (8 + cache.config.associativity * 15),
        ]

        for s_idx in range(min(len(cache.sets), limit_sets)):
            s = cache.sets[s_idx]
            ways_str = []
            for w in s.ways:
                if w.valid:
                    ways_str.append(f"T:{w.tag} B:{w.block_number}")
                else:
                    ways_str.append("[EMPTY]")
            lines.append(f"{s_idx:<5} | " + " | ".join(f"{st:<12}" for st in ways_str))

        if len(cache.sets) > limit_sets:
            lines.append(f"... ({len(cache.sets) - limit_sets} more sets omitted for brevity) ...")

        return "\n".join(lines)

    @staticmethod
    def save_matplotlib_dashboard(
        result: SimulationResult,
        output_filepath: str = "cache_dashboard.png",
    ) -> bool:
        """Export a multi-panel visual dashboard using matplotlib."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            fig, axs = plt.subplots(2, 2, figsize=(14, 10))
            fig.suptitle(
                f"CacheScope Analysis: {result.workload_name} ({result.config.summary()})",
                fontsize=13,
                fontweight="bold",
            )

            # Panel 1: Hits vs Misses Pie
            m = result.metrics
            ax1 = axs[0, 0]
            ax1.pie(
                [m.hits, m.misses],
                labels=[f"Hits ({m.hits})", f"Misses ({m.misses})"],
                autopct="%1.1f%%",
                startangle=140,
                colors=["#2ecc71", "#e74c3c"],
            )
            ax1.set_title("Overall Hit vs Miss Distribution")

            # Panel 2: 3C Miss Breakdown
            ax2 = axs[0, 1]
            categories = ["Compulsory", "Capacity", "Conflict"]
            counts = [m.compulsory_misses, m.capacity_misses, m.conflict_misses]
            colors = ["#3498db", "#9b59b6", "#e67e22"]
            bars = ax2.bar(categories, counts, color=colors)
            ax2.set_ylabel("Miss Count")
            ax2.set_title("3C Miss Classification Breakdown")
            for bar in bars:
                yval = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2, yval + 0.1, f"{int(yval)}", ha="center", va="bottom")

            # Panel 3: Set Access Heatmap
            ax3 = axs[1, 0]
            counts_arr = np.array(m.set_access_counts)
            if len(counts_arr) > 0:
                num_sets = len(counts_arr)
                cols = 16 if num_sets >= 16 else max(1, num_sets)
                rows = math.ceil(num_sets / cols)
                padded = np.zeros(rows * cols)
                padded[:num_sets] = counts_arr
                grid = padded.reshape((rows, cols))
                im = ax3.imshow(grid, cmap="YlOrRd", aspect="auto")
                plt.colorbar(im, ax=ax3, label="Accesses")
                ax3.set_title("Set Access Frequency Heatmap")
                ax3.set_xlabel("Set Column Index")
                ax3.set_ylabel("Set Row Index")

            # Panel 4: Cumulative Hits Over Time
            ax4 = axs[1, 1]
            steps = [e.step for e in result.events]
            cumulative_hits = np.cumsum([1 if e.is_hit else 0 for e in result.events])
            hit_rates_over_time = [
                (cumulative_hits[i] / (i + 1)) * 100.0 for i in range(len(steps))
            ] if steps else []

            ax4.plot(steps, hit_rates_over_time, color="#2980b9", lw=2)
            ax4.set_title("Hit Rate Convergence Over Time (%)")
            ax4.set_xlabel("Access Step")
            ax4.set_ylabel("Cumulative Hit Rate (%)")
            ax4.grid(True, linestyle="--", alpha=0.6)
            ax4.set_ylim([0, 105])

            plt.tight_layout()
            plt.savefig(output_filepath, dpi=150)
            plt.close()
            return True
        except Exception as ex:
            print(f"Warning: could not generate matplotlib chart: {ex}")
            return False

    @staticmethod
    def save_whatif_comparison_chart(
        experiment: WhatIfExperiment,
        output_filepath: str = "whatif_comparison.png",
    ) -> bool:
        """Export a comparison chart for What-If experiments."""
        try:
            import matplotlib.pyplot as plt

            configs = [experiment.baseline_result.config.name] + [
                r.config.name for r in experiment.alternative_results
            ]
            hit_rates = [experiment.baseline_result.metrics.hit_rate] + [
                r.metrics.hit_rate for r in experiment.alternative_results
            ]
            amats = [experiment.baseline_result.metrics.amat] + [
                r.metrics.amat for r in experiment.alternative_results
            ]

            fig, ax1 = plt.subplots(figsize=(10, 6))
            color = "#2980b9"
            ax1.set_xlabel("Cache Configuration", fontweight="bold")
            ax1.set_ylabel("Hit Rate (%)", color=color, fontweight="bold")
            bars = ax1.bar(configs, hit_rates, color=color, alpha=0.7, width=0.4, label="Hit Rate (%)")
            ax1.tick_params(axis="y", labelcolor=color)
            ax1.set_ylim([0, 105])

            # Secondary axis for AMAT
            ax2 = ax1.twinx()
            color = "#c0392b"
            ax2.set_ylabel("AMAT (cycles)", color=color, fontweight="bold")
            ax2.plot(configs, amats, color=color, marker="o", lw=2, label="AMAT")
            ax2.tick_params(axis="y", labelcolor=color)

            for bar in bars:
                y = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width() / 2, y + 1, f"{y:.1f}%", ha="center", va="bottom", fontsize=9)

            plt.title("CacheScope What-If Comparison: Hit Rate & AMAT", fontsize=12, fontweight="bold")
            fig.autofmt_xdate(rotation=20)
            plt.tight_layout()
            plt.savefig(output_filepath, dpi=150)
            plt.close()
            return True
        except Exception as ex:
            print(f"Warning: could not generate whatif comparison chart: {ex}")
            return False
