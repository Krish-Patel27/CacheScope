"""
database.py — SQLite storage and export for CacheScope experiments.

Stores experiments, configurations, and metrics for historical benchmarking,
multi-experiment comparisons, and exporting to CSV or JSON formats.
"""

from __future__ import annotations
import csv
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional
from cache_analyzer.simulator import SimulationResult
from cache_analyzer.whatif import WhatIfExperiment


class CacheDatabase:
    """Manages SQLite storage and historical query logging for CacheScope."""

    def __init__(self, db_path: str = "cachescope.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    date_str TEXT NOT NULL,
                    workload_name TEXT NOT NULL,
                    total_accesses INTEGER NOT NULL,
                    notes TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id INTEGER NOT NULL,
                    is_baseline BOOLEAN NOT NULL,
                    config_name TEXT NOT NULL,
                    cache_size INTEGER NOT NULL,
                    block_size INTEGER NOT NULL,
                    associativity INTEGER NOT NULL,
                    num_lines INTEGER NOT NULL,
                    num_sets INTEGER NOT NULL,
                    policy TEXT NOT NULL,
                    hit_rate REAL NOT NULL,
                    miss_rate REAL NOT NULL,
                    amat REAL NOT NULL,
                    compulsory_misses INTEGER NOT NULL,
                    capacity_misses INTEGER NOT NULL,
                    conflict_misses INTEGER NOT NULL,
                    evictions INTEGER NOT NULL,
                    FOREIGN KEY (experiment_id) REFERENCES experiments (id)
                )
            """)
            conn.commit()

    def save_simulation(self, result: SimulationResult, experiment_name: Optional[str] = None, notes: str = "") -> int:
        """Save a single simulation run as an experiment."""
        name = experiment_name or f"Sim_{result.workload_name}_{result.config.name}"
        now = time.time()
        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiments (name, timestamp, date_str, workload_name, total_accesses, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, now, date_str, result.workload_name, result.metrics.total_accesses, notes))
            exp_id = cursor.lastrowid

            cfg = result.config
            met = result.metrics
            cursor.execute("""
                INSERT INTO configurations (
                    experiment_id, is_baseline, config_name, cache_size, block_size,
                    associativity, num_lines, num_sets, policy, hit_rate, miss_rate,
                    amat, compulsory_misses, capacity_misses, conflict_misses, evictions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp_id, True, cfg.name, cfg.cache_size, cfg.block_size,
                cfg.associativity, cfg.num_lines, cfg.num_sets, cfg.replacement_policy,
                met.hit_rate, met.miss_rate, met.amat, met.compulsory_misses,
                met.capacity_misses, met.conflict_misses, met.evictions
            ))
            conn.commit()
            return exp_id

    def save_whatif(self, whatif: WhatIfExperiment, experiment_name: str, notes: str = "") -> int:
        """Save an entire what-if comparison suite under a single experiment ID."""
        now = time.time()
        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        b_res = whatif.baseline_result

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiments (name, timestamp, date_str, workload_name, total_accesses, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (experiment_name, now, date_str, b_res.workload_name, b_res.metrics.total_accesses, notes))
            exp_id = cursor.lastrowid

            # Save baseline
            b_cfg = b_res.config
            b_met = b_res.metrics
            cursor.execute("""
                INSERT INTO configurations (
                    experiment_id, is_baseline, config_name, cache_size, block_size,
                    associativity, num_lines, num_sets, policy, hit_rate, miss_rate,
                    amat, compulsory_misses, capacity_misses, conflict_misses, evictions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp_id, True, b_cfg.name, b_cfg.cache_size, b_cfg.block_size,
                b_cfg.associativity, b_cfg.num_lines, b_cfg.num_sets, b_cfg.replacement_policy,
                b_met.hit_rate, b_met.miss_rate, b_met.amat, b_met.compulsory_misses,
                b_met.capacity_misses, b_met.conflict_misses, b_met.evictions
            ))

            # Save alternatives
            for alt in whatif.alternative_results:
                a_cfg = alt.config
                a_met = alt.metrics
                cursor.execute("""
                    INSERT INTO configurations (
                        experiment_id, is_baseline, config_name, cache_size, block_size,
                        associativity, num_lines, num_sets, policy, hit_rate, miss_rate,
                        amat, compulsory_misses, capacity_misses, conflict_misses, evictions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exp_id, False, a_cfg.name, a_cfg.cache_size, a_cfg.block_size,
                    a_cfg.associativity, a_cfg.num_lines, a_cfg.num_sets, a_cfg.replacement_policy,
                    a_met.hit_rate, a_met.miss_rate, a_met.amat, a_met.compulsory_misses,
                    a_met.capacity_misses, a_met.conflict_misses, a_met.evictions
                ))

            conn.commit()
            return exp_id

    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all historical experiments stored in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, COUNT(c.id) as config_count
                FROM experiments e
                LEFT JOIN configurations c ON e.id = c.experiment_id
                GROUP BY e.id
                ORDER BY e.timestamp DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_experiment_details(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """Fetch complete records for an experiment including all its configurations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
            exp_row = cursor.fetchone()
            if not exp_row:
                return None

            cursor.execute("SELECT * FROM configurations WHERE experiment_id = ?", (experiment_id,))
            config_rows = [dict(r) for r in cursor.fetchall()]

            res = dict(exp_row)
            res["configurations"] = config_rows
            return res

    def export_to_json(self, experiment_id: int, filepath: str):
        """Export experiment data to JSON file."""
        data = self.get_experiment_details(experiment_id)
        if not data:
            raise ValueError(f"Experiment {experiment_id} not found.")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def export_to_csv(self, experiment_id: int, filepath: str):
        """Export experiment configurations and metrics to CSV file."""
        data = self.get_experiment_details(experiment_id)
        if not data or not data["configurations"]:
            raise ValueError(f"No configuration data found for experiment {experiment_id}.")

        configs = data["configurations"]
        fieldnames = list(configs[0].keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in configs:
                writer.writerow(row)
