#!/usr/bin/env python3
"""Convenience launcher for CacheScope Streamlit Web Dashboard."""

import subprocess
import sys

def launch_dashboard():
    print("Launching CacheScope Web Dashboard on http://localhost:8501...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])

if __name__ == "__main__":
    launch_dashboard()
