"""
trace_loader.py — Load memory access traces from external files.

Supports:
- Plain text (.txt / .trace): decimal or hex addresses (e.g. 0x1000, 4096)
- Dinero IV / Valgrind format: [access_type address size] (e.g., "0 0x7fff0010 4")
- CSV files: with header containing "address", "addr", "Address", etc.
"""

from __future__ import annotations
import csv
import os
import re
from typing import List, Optional
from cache_analyzer.workload.base import WorkloadGenerator


class TraceLoader(WorkloadGenerator):
    """Loads memory addresses from disk or in-memory text buffers."""

    def __init__(self, filepath: Optional[str] = None, text_content: Optional[str] = None, **kwargs):
        super().__init__(name="TRACE_LOADER", filepath=filepath, **kwargs)
        self.filepath = filepath
        self.text_content = text_content

    def generate(self) -> List[int]:
        if self.text_content is not None:
            return self._parse_lines(self.text_content.splitlines())

        if self.filepath is not None:
            if not os.path.exists(self.filepath):
                raise FileNotFoundError(f"Trace file not found: {self.filepath}")

            _, ext = os.path.splitext(self.filepath.lower())
            if ext == ".csv":
                return self._parse_csv(self.filepath)
            else:
                with open(self.filepath, "r", encoding="utf-8", errors="replace") as f:
                    return self._parse_lines(f.readlines())

        raise ValueError("TraceLoader requires either filepath or text_content.")

    def _parse_lines(self, lines: List[str]) -> List[int]:
        addresses: List[int] = []
        for line_num, line in enumerate(lines, 1):
            clean = line.strip()
            if not clean or clean.startswith("#") or clean.startswith("//"):
                continue

            # Check if line contains space-separated tokens (e.g. Dinero IV format: "0 0x1234 4")
            tokens = clean.split()
            addr_token = tokens[1] if len(tokens) >= 2 and tokens[0] in ("0", "1", "2", "r", "w", "R", "W") else tokens[0]

            try:
                # Handle hex or decimal
                if addr_token.lower().startswith("0x"):
                    addr = int(addr_token, 16)
                else:
                    # If it contains a-f letters, treat as hex without 0x
                    if re.search(r"[a-fA-F]", addr_token):
                        addr = int(addr_token, 16)
                    else:
                        addr = int(addr_token, 10)
                addresses.append(addr)
            except ValueError:
                # Skip invalid lines gracefully
                continue

        return addresses

    def _parse_csv(self, filepath: str) -> List[int]:
        addresses: List[int] = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            addr_col = 0
            if header:
                # Search for column name
                for idx, col in enumerate(header):
                    if col.strip().lower() in ("address", "addr", "memory_address", "address_hex"):
                        addr_col = idx
                        break
            
            for row in reader:
                if not row or len(row) <= addr_col:
                    continue
                token = row[addr_col].strip()
                if not token:
                    continue
                try:
                    if token.lower().startswith("0x") or re.search(r"[a-fA-F]", token):
                        addresses.append(int(token, 16))
                    else:
                        addresses.append(int(token, 10))
                except ValueError:
                    continue

        return addresses

    def description(self) -> str:
        source = self.filepath or "in-memory text"
        return f"Trace loaded from {source}"
