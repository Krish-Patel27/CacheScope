#!/usr/bin/env python3
"""Convenience runner script for CacheScope CLI."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cache_analyzer.main import main

if __name__ == "__main__":
    main()
